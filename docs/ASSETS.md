# Ресурсы Brickfall

В текущей игре фон, кирпичи, платформа, мяч, кнопки и небольшие эффекты
рисуются средствами Pygame. Готовые чужие спрайты не используются.
Используются установленные системные Segoe UI Regular и Bold.
При их отсутствии выбирается Arial или DejaVu Sans, затем стандартный шрифт Pygame.
Файлы шрифтов в репозиторий не копируются.

Сайт использует HTML, CSS и системные шрифты. Внешних шрифтов и библиотек
JavaScript нет. Фотография баннера хранится локально:
`static/assets/ben-allan-brick-grid.jpg`.

Автор фотографии — Ben Allan. Источник:
https://unsplash.com/photos/black-and-white-concrete-building-Chcm0mTg0hU.
Лицензия: https://unsplash.com/license. Подпись автора и ссылка сохранены
под баннером Leaderboard. При просмотре сайта файл загружается с самого
сервера Brickfall, запрос к Unsplash не нужен.

`docs/skice.png` — исходная эскизная иллюстрация к школьному заданию.
`docs/brickfall-current.png` — снимок текущей игры; `docs/brickfall-menu.png` —
снимок главного меню. docs/brickfall-login.png показывает форму входа.
Эти снимки получены из настоящей отрисовки Pygame.

docs/site-leaderboard-desktop.png, docs/site-leaderboard-mobile.png,
docs/site-player-desktop.png, docs/site-player-mobile.png,
docs/site-rules.png и docs/site-rules-mobile.png — снимки сайта из Chrome.
Мобильный снимок сделан с областью 390×844, а не обрезкой десктопной страницы.
Десктопная область — 1440×900; длинные страницы сняты целиком.
Использовалась отдельная временная база с демонстрационными именами
DemoPlayer, GridRunner и BrickMaster. Локальные аккаунты и их данные
в эти снимки не включены.

Старые изображения `docs/brickfall-robot.png`, `docs/brickfall-redesign.png`,
`docs/brickfall-preview.png` и `client/assets/menu_bg.png` сохранены как
материалы предыдущих версий. Они не загружаются текущей игрой.
Происхождение и лицензия исходного `menu_bg.png` неизвестны.
Босс и его механики больше не используются.

Ранее рассматривались ресурсы OpenGameArt и Kenney, но их изображения
не включены в текущую игру.
