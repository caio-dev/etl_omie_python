Este repositório contém alguns scripts de ETL em python.

- O objetivo inicial é coletar dados via API do ERP OMIE e inserir em um banco de dados Postgrees;
- O script atende mais de 1 app do ERP, varrendo eles de maneira sequencial;
- O script é procedural, podendo ser otimizado de maneira significativa (execuções simultâneas);
- Alguns trechos contém menções à estruturas do airflow, pois o script foi usado no orquestrador também.
