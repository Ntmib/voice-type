# Voice-Type

Свой голосовой ввод в стиле [Wispr Flow](https://wisprflow.ai) — работает в
любом приложении на Mac и iPhone, данные ходят только через **твой** сервер.

Зажал клавишу → внизу экрана пилюля с живой волной → сказал → отпустил →
текст с расставленной пунктуацией в буфере обмена → Cmd+V.

```
[Mac / iPhone] → аудио → [твой VPS] → Deepgram (распознавание)
                                    → LLM (пунктуация) → текст
```

## Что понадобится

| Что | Зачем | Где взять |
|---|---|---|
| VPS с Ubuntu/Debian | сервер распознавания | любой хостинг, хватит самого дешёвого |
| Ключ Deepgram | распознавание речи | [console.deepgram.com](https://console.deepgram.com) — дают $200 кредита, надолго хватит |
| Ключ OpenRouter (опционально) | пунктуация | [openrouter.ai](https://openrouter.ai) — без него текст будет без знаков препинания |
| Домен или поддомен (опционально, но рекомендуется) | HTTPS-шифрование | см. раздел «Домен и HTTPS» |

---

## Самый простой путь — попроси Claude 🤖

Не дружишь с терминалом? Не нужно. Если у тебя есть
[Claude Code](https://claude.com/claude-code) (или приложение Claude с
доступом к компьютеру) — просто скопируй ему этот промпт целиком и подставь
свои данные:

```text
Установи мне Voice-Type из репозитория https://github.com/Ntmib/voice-type
по его README.

Мои данные:
- VPS: IP <впиши>, доступ по SSH <ключ или попроси меня ввести пароль>
- Ключ Deepgram: положи в .env на сервере, я пришлю его в файле/вставлю сам
- Ключ OpenRouter (для пунктуации): аналогично
- Домен: <есть такой-то / нет — предложи варианты>

Сделай всё сам: сервер + systemd + nginx + HTTPS (если есть домен),
потом Mac-клиент через install.sh. Где нужны мои действия (DNS-запись,
разрешения macOS, ключи) — говори по шагам простым языком.
```

Claude прочитает README и пройдёт все шаги за тебя, спрашивая только то,
что можешь сделать лишь ты (выдать разрешения macOS, добавить DNS-запись
в панели домена). Именно так этот проект и разрабатывался.

iPhone настраивается вообще без терминала — руками за 5 минут:
[clients/ios/README.md](clients/ios/README.md).

---

## Ручная установка

<details>
<summary><b>Как пользоваться командами ниже (если делаешь без Claude)</b></summary>

- **Терминал на Mac**: Cmd+Пробел → набери «Терминал» → Enter. Появится
  окно для текстовых команд.
- **Зайти на сервер**: в терминале набери `ssh root@IP-твоего-сервера`
  и Enter (пароль/ключ дал хостинг). Всё из Части 1 вводится там,
  на сервере.
- Команды из серых блоков копируй целиком, вставляй в терминал (Cmd+V)
  и жми Enter. Одна строка = одна команда; блок из нескольких строк можно
  вставить разом.
- `nano файл` — открывает простейший редактор прямо в терминале: правишь
  текст, потом Ctrl+O (сохранить), Enter, Ctrl+X (выйти).

</details>

## Часть 1. Сервер

```bash
# на VPS
git clone https://github.com/Ntmib/voice-type.git
cd voice-type/server
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env        # впиши ключи; токен сгенерируй так: openssl rand -hex 24
```

Проверка, что всё живо:

```bash
venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8100
# в соседнем терминале: curl localhost:8100/health  →  {"status":"ok"}
```

### Автозапуск (systemd)

`/etc/systemd/system/voice-type.service`:

```ini
[Unit]
Description=Voice-Type API
After=network.target

[Service]
User=voice-type
WorkingDirectory=/home/voice-type/voice-type/server
EnvironmentFile=/home/voice-type/voice-type/server/.env
ExecStart=/home/voice-type/voice-type/server/venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8100
Restart=always
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd -m voice-type          # отдельный юзер, не root
sudo systemctl enable --now voice-type
```

### nginx (вход снаружи)

`/etc/nginx/sites-available/voice-type` (символьная ссылка в `sites-enabled/`):

```nginx
server {
    listen 80;
    server_name voice.example.com;   # твой домен (или IP сервера, если домена нет)

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        client_max_body_size 25M;
        proxy_read_timeout 60s;
    }
}
```

### Домен и HTTPS

Без HTTPS голос и токен летают по сети открытым текстом — для теста сойдёт,
для постоянной работы заведи шифрование. Сертификаты выдают только на
доменные имена, поэтому:

1. **Есть любой свой домен** (например, `example.com` у любого
   регистратора)? Поддомен бесплатный: в DNS-панели домена добавь запись
   типа **A** с именем `voice` и значением — IP твоего VPS. Получится
   `voice.example.com`. ⚠️ Если панель при создании поддомена сама
   добавила вторую A-запись с чужим IP (заглушка хостинга) — удали её,
   должна остаться ровно одна.
2. **Домена нет** — самый дешёвый стоит пару долларов в год (Namecheap,
   reg.ru и т.п.). Либо временно работай по `http://IP-сервера` без
   шифрования.
3. Через 5–15 минут (DNS должен разъехаться) выпусти сертификат:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d voice.example.com
```

Certbot сам включит HTTPS в nginx и будет продлевать сертификат. Проверка:
`curl https://voice.example.com/health` → `{"status":"ok"}`.

---

## Часть 2. Mac-клиент

Эти команды вводятся уже не на сервере, а в терминале самого Mac
(Cmd+Пробел → «Терминал»):

```bash
git clone https://github.com/Ntmib/voice-type.git
cd voice-type/clients/mac
cp .env.example .env
nano .env        # VOICETYPE_URL=https://voice.example.com  +  твой токен
./install.sh
```

Скрипт ставит зависимости, собирает мини-приложение VoiceType.app и
включает автозапуск. macOS попросит разрешения — все три нужно дать:

1. **Универсальный доступ** → включить VoiceType
2. **Мониторинг ввода** → включить VoiceType
3. **Микрофон** — при первой записи

(Настройки → Конфиденциальность и безопасность. Если VoiceType в списке
нет — «+» и добавь `~/Library/Application Support/VoiceType/VoiceType.app`.)

Использование:

- **Зажать правый Command** → пилюля с волной внизу экрана = запись идёт
- **Отпустить** → «обработка» → «✓ Cmd+V» = текст в буфере
- **Cmd+V** — вставить куда угодно

Проверка визуала без микрофона: `python3 voice_type.py --demo`.
Лог: `/tmp/voicetype.log`.

---

## Часть 3. iPhone

Кнопка через штатное приложение «Команды» (5 минут, без установки
программ): пошаговая инструкция — **[clients/ios/README.md](clients/ios/README.md)**.
Вешается на Action Button или двойной тап по крышке телефона.

---

## Если не работает

| Симптом | Причина |
|---|---|
| Пилюля не появляется на Mac | не выданы разрешения (см. Часть 2), потом перезапуск: `launchctl kickstart -k gui/$(id -u)/com.voicetype.agent` |
| Текст без знаков препинания | нет `OPENROUTER_API_KEY` на сервере |
| `401 Unauthorized` | токен клиента ≠ токен сервера |
| Первый запрос медленный (~10 с) | норма: прогрев соединений после рестарта сервера, дальше ~1.5 с |
| OpenRouter отвечает 403 | твой VPS в регионе с блокировкой — задай `OPENROUTER_PROXY` в server/.env |

## Структура

```
server/          — API сервер (FastAPI + Deepgram + OpenRouter)
clients/mac/     — Mac-клиент (запись, пилюля-индикатор, install.sh)
clients/ios/     — Инструкция для Apple Shortcuts
SPEC.md          — Спецификация проекта
```

## Лицензия

MIT
