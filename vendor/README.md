# Локальные зависимости интерфейса

Каталог содержит зафиксированные браузерные зависимости, без которых карта,
графики или Excel-выгрузка не работают. Они хранятся в проекте намеренно:
недоступность CDN не должна ломать старт страниц.

| Пакет | Версия | Назначение |
|---|---:|---|
| Leaflet | 1.9.4 | Карта |
| Leaflet.markercluster | 1.5.3 | Кластеризация маркеров |
| Leaflet.draw | 1.0.4 | Рисование областей |
| Chart.js | 4.4.1 | Графики |
| chartjs-plugin-datalabels | 2.2.0 | Подписи значений |
| SheetJS Community Edition | 0.18.5 | Excel-выгрузка |
| Montserrat (`@fontsource`) | 5.0.18 | Корпоративная типографика, кириллица и латиница |

Лицензии и лицензионные метаданные находятся рядом с файлами пакетов.

## Контрольные суммы основных файлов

```text
leaflet/leaflet.js                             DB49D009C841F5CA34A888C96511AE936FD9F5533E90D8B2C4D57596F4E5641A
leaflet.markercluster/leaflet.markercluster.js 1E4E1D22972A3926F48598E0CAF14E3FE7049835D428A344FED4F9E3665B3508
leaflet-draw/leaflet.draw.js                   B22A1F7385308E5ADADD85A4C2D84E9FC523EBD70D37868CBA0FE2387362460B
chartjs/chart.umd.min.js                       D2AF8974E95271638772E9E9524DB5B9A6F58D6EC2D5D781400447B4A31C681E
chartjs/chartjs-plugin-datalabels.min.js       20C08F3D9C6D2EF76DF6D6A6F1127C0013339FE32ADD24222276C398C6308C38
xlsx/xlsx.full.min.js                          C9506197CAF809A075B6DEE1DA0D36FB19DA7158FFE8A88E7B0C96C5D8623C99
```

При обновлении зависимости необходимо одновременно обновить:

1. сам файл и связанные CSS-ресурсы;
2. версию и контрольную сумму в этом документе;
3. файл лицензии;
4. проверки в `tests/test_local_vendor_assets.py`;
5. полный набор тестов и браузерную проверку страниц без доступа к CDN.
