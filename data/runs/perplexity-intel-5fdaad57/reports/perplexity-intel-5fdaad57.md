# Relatório de Descoberta de Datasets no Projeto 100K

Este relatório sintetiza os datasets identificados até o momento no âmbito do projeto 100K, que investiga as influências das pressões antrópicas na dinâmica do material orgânico na bacia do Rio Tietê. A análise contempla a cobertura por níveis hierárquicos, formatos de acesso, lacunas identificadas em relação às fontes prioritárias, e recomenda próximos passos para ampliar e validar a base de dados.

---

## 1. Cobertura por Nível Hierárquico

Foram encontrados 30 datasets distribuídos entre os níveis macro, meso, bridge e micro. A maior concentração está no nível macro, refletida por 22 datasets, o que é coerente com o foco em processos de grande escala e operações de reservatórios na bacia do Rio Tietê.

### Nível Macro
A maioria dos datasets de nível macro provém de fontes governamentais e acadêmicas, abordando temas como morfometria de bacias, operações de reservatórios, qualidade da água, hidrologia e condições de seca. Destacam-se fontes como NOAA, USGS, EPA, e agências estaduais de água, além de relatórios e análises em formato PDF.

### Nível Meso
Há uma quantidade menor de datasets no nível meso, incluindo dados de operações de reservatórios, níveis de água, vazões e condições de seca, principalmente provenientes de fontes como USACE e entidades estaduais.

### Nível Bridge
Embora não explicitamente listado na relação, alguns datasets de nível macro também podem atuar como ponte, fornecendo informações que conectam processos de grande escala às dinâmicas locais, especialmente aqueles que envolvem análises de bacias e áreas específicas.

### Nível Micro
Nenhum dataset de nível micro foi identificado até o momento, indicando lacuna na disponibilidade de dados de monitoramento em escala de ponto ou de pequenas unidades de análise.

---

## 2. Cobertura por Formato de Acesso

Os datasets apresentam diferentes formatos de acesso, o que impacta diretamente na complexidade de ETL (Extração, Transformação, Carga).

- **Download Direto (Structured):** 3 datasets, incluindo Water Quality Portal (WQP) e Savannah River Bathymetric Model, oferecem acesso direto e estruturado, facilitando a integração automática.
- **Portal Web (Semi-estruturado):** A maioria dos datasets (aproximadamente 20) está disponível via portais web, incluindo USGS, EPA, NOAA, e entidades estaduais. Esses geralmente requerem extração manual ou automatizada via scraping.
- **PDF (Semi-estruturado):** Cerca de 7 datasets estão disponíveis em formato PDF, como análises de bacias e relatórios de landscape analysis, demandando processos adicionais de extração de dados.
- **Web Portal (Contextual/Informacional):** Alguns datasets, especialmente aqueles de informações contextuais (ex.: Thurmond Pertinent Data), estão acessíveis apenas por páginas web, sem formato de dados estruturados.

Essa diversidade implica que o esforço de ETL será maior para datasets em PDF e páginas web, enquanto os dados estruturados podem ser integrados com menor esforço.

---

## 3. Lacunas e Fontes Prioritárias Não Cobertas

Apesar da variedade de fontes, algumas lacunas relevantes foram identificadas em relação às fontes prioritárias listadas inicialmente:

- **ANA HidroWeb:** Não há datasets específicos de hidrologia em formato estruturado ou em portais acessíveis. Essa fonte é fundamental para dados de vazões, níveis e precipitação na bacia do Tietê.
- **CETESB QUALAR:** Ausência de dados de qualidade da água, incluindo análises químicas, bacteriológicas e de CDOM, essenciais para avaliar eutrofização e impacto de atividades humanas.
- **SNIS:** Dados de saneamento, como coleta e tratamento de esgoto, não aparecem, limitando a compreensão do impacto antropogênico na qualidade da água.
- **MapBiomas:** Não há cobertura de uso do solo, que é crucial para relacionar desmatamento, urbanização e impacto na dinâmica do material orgânico.
- **INPE PRODES/DETER:** Dados de desmatamento e queimadas não foram identificados, embora sejam relevantes para entender mudanças na cobertura vegetal.
- **INPE BDQueimadas:** Ausência de informações sobre queimadas na bacia, que podem influenciar a matéria orgânica e a qualidade da água.
- **ONS:** Dados de operação de usinas hidrelétricas, além de vazões e níveis, não estão presentes, limitando análises de impacto operacional.
- **IBGE SIDRA:** Dados demográficos e de atividade agropecuária, que podem influenciar a carga de matéria orgânica, também não aparecem.
- **Sensoriamento Remoto (Sentinel-2 / Landsat):** Não há datasets de satélites de alta resolução, essenciais para análises de uso do solo, cobertura vegetal e CDOM.
- **Artigos CDOM/MOD nos reservatórios do Tietê:** Nenhuma publicação ou dado específico sobre CDOM ou satélites no contexto do Tietê.

Essa lacuna indica necessidade de buscas adicionais, especialmente em fontes de dados de uso do solo, qualidade da água, desmatamento, queimadas e operação de usinas.

---

## 4. Próximos Passos

### Busca e Acesso Manual
Devido às lacunas, recomenda-se buscar manualmente fontes específicas, como os portais do ANA HidroWeb, CETESB QUALAR, MapBiomas e INPE, além de consultar bases de dados do IBGE e ONS. A análise de artigos científicos, especialmente aqueles que abordam CDOM, MODIS, Landsat, ou estudos específicos na bacia do Tietê, será fundamental para complementar os dados existentes.

### Validações Cruzadas Prioritárias
Para garantir consistência e ampliar a confiabilidade, recomenda-se realizar validações cruzadas entre variáveis de diferentes fontes. Exemplos incluem:

- **SNIS × CETESB DBO:** Comparar dados de esgoto doméstico e industrial para verificar coerência na carga de matéria orgânica.
- **MapBiomas × CETESB Turbidez:** Relacionar uso do solo com turbidez na água, buscando hipóteses de causa-efeito entre desmatamento e aumento de matéria em suspensão.
- **Clorofila in situ × Satélite:** Validar dados de clorofila obtidos por satélites com medições locais, aprimorando calibração de sensores remotos.
- **Uso do solo × COT reservatórios:** Analisar a influência do uso do solo na qualidade da água nos reservatórios, apoiando hipóteses centrais do projeto.

### Expansão de Dados
A inclusão de dados de desmatamento, queimadas, uso do solo, saneamento e operação de usinas hidrelétricas será essencial para uma compreensão integrada do sistema. Além disso, a aquisição de dados de satélites de alta resolução (Sentinel-2, Landsat) e dados de qualidade da água de fontes como CETESB e INPE permitirá análises mais detalhadas e calibradas.

### Validação e Integração
A integração de datasets de diferentes fontes e formatos deve seguir uma estratégia de validação cruzada, com atenção especial à coerência temporal e espacial. A padronização de variáveis e unidades facilitará a análise comparativa e a modelagem de processos.

---

## Conclusão

A descoberta atual de 30 datasets revela uma base sólida de informações sobre morfometria, operações de reservatórios, hidrologia e qualidade da água, principalmente em nível macro. Contudo, há lacunas importantes em dados de uso do solo, saneamento, desmatamento, queimadas e operação de usinas, que devem ser priorizadas em buscas futuras.

A diversidade de formatos exige planejamento cuidadoso de ETL, especialmente para dados em PDF e páginas web. A validação cruzada entre variáveis de diferentes fontes será crucial para garantir a consistência e robustez das análises.

Por fim, recomenda-se uma estratégia integrada de busca, validação e aquisição de dados adicionais, com foco em fontes de alta qualidade e resolução, para suportar as hipóteses centrais do projeto e aprofundar a compreensão das dinâmicas do sistema hidroambiental do Rio Tietê.