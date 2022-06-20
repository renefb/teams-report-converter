# Teams Attendance Report Converter


<div style="text-align:center">
    <a href="#">
        <img width="30" src="https://flagpedia.net/data/flags/h80/br.webp">
    </a>
    &nbsp;
    <a href="/">
        <img width="30" height="20" src="https://flagpedia.net/data/flags/h80/us.webp">
    </a>
</div>


Esta ferramenta gera planilhas de cálculo de frequência de participantes de eventos ao vivo no MS Teams a partir dos [relatórios de engajamento](https://support.microsoft.com/pt-br/office/obter-um-relat%C3%B3rio-de-envolvimento-do-participante-para-um-evento-teams-ao-vivo-b3101733-2eda-48a6-aeb3-de2f2bfecb3a).

No lugar disto:
```csv
SessionId,ParticipantId,FullName,UserAgent,UtcEventTimestamp,Action,Role
518ca2fd-...,johndoe@test.net,John Doe,Mozila/5.0...,1/25/2022 4:48:08 PM,Joined,Attendee
39f73ed2-...,mbrigs@corp.co,Mark Brigs,SignalR...,1/25/2022 4:51:13 PM,Joined,Attendee
518ca2fd-...,johndoe@test.net,John Doe,Mozila/5.0...,1/25/2022 5:25:54 PM,Left,Attendee
```
Você terá isto:
| ParticipantId    | FullName   | Role     | AttendanceInMinutes | AttendanceFormatted |
|------------------|------------|----------|---------------------|---------------------|
| johndoe@test.net | John Doe   | Attendee | 37.1                | 000h37min04s        |
| mbrigs@corp.co   | Mark Brigs | Attendee | 65.6                | 001h05min36s        |


Você pode conferir a [demo aqui](https://colab.research.google.com/drive/1c1Swbp5PXZu8bf6t1K1ksbqYVr4utzOl?usp=sharing).


## Instalação

O conversor pode ser obtido diretamente do diretório [PyPI](https://pypi.org/project/teams-report-converter):

```python
pip install teams-report-converter
```


## Como usar

O conversor pode ser usado como uma aplicação de linha de comando (CLI), bem como um pacote importado pela sua própria aplicação em python.


### Usando como CLI:

```cmd
convert-teams-report -f <caminho-para-csv-original> -s <data-hora-de-início-do-evento> -e <data-hora-do-fim-do-evento> -tz <fuso-horário-do-evento> -o <caminho-para-a-planilha-de-resultado>
```
Neste cenário, o conversor utiliza os seguintes parâmetros:
- `-f`: caminho do dispositivo onde se encontra o relatório gerado pelo MS Teams, por exemplo: "C:\Downloads\AttendeeReport.csv"
- `-s`: data e hora do início do evento no formato "%AAAA-%MM-%DD %hh:%mm:%ss" (envolvidos em aspas duplas)
- `-e`: data e hora do fim do evento no formato "%AAAA-%MM-%DD %hh:%mm:%ss" (envolvidos em aspas duplas)
- `-o`: caminho do dispositivo onde você deseja salvar a planilha resultante, por exemplo "C:\Relatorios\frequencia.xlsx" ou, simplesmente, "C:\Relatorios" (neste último caso, por padrão, a planilha será nomeada como "output.xlsx")
- `-tz`: fuso horário utilizado na indicação da data e hora de início e fim do evento (para o fuso horário de Brasília, você pode usar o valor "America/Sao_Paulo"; demais casos, verifique [aqui](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) a lista completa de valores possíveis)

Observe que este é o único cenário que efetivamente gera a planilha pronta para uso.


### Usando como um pacote importado pela sua própria aplicação python

Você também pode usar o conversor como um pacote apenas para processar o relatório original e aplicar seus próprios cálculos (como, por exemplo, avaliar os participantes do evento como "aprovados" ou "reprovados" de acordo com uma frequência mínima). Neste cenário, a classe Converter três objetos do tipo Pandas.DataFrame que você poderá manipular conforme as suas necessidades:

```python
from teams_report_converter import Converter

converter = Converter(report_content='AttendeeReport.csv', 
                      event_start='2021-11-03 15:00:00', 
                      event_end='2021-11-03 17:00:00', 
                      local_tz='America/Sao_Paulo')
```
A partir disso, você poderá chamar `converter.data` para acessar os dados originais, `converter.sessions` para listar todas as sessões com os respectivos ingressos (*joined*) e saídas (*left*) e `converter.attendance` para a frequência válida de cada participante ao evento.


## Como as frequências são calculadas

A tabela abaixo demonstra como os registros de ingresso (*joined*) e saída (*left*) de um usuário, em uma sessão específica, extraídos dos dados originais são processados em diferentes cenários:

| Ingresso (*Joined*)       | Saída (*Left*)               | Ingresso Ajustado         | Saída Ajustada         | Cálculo da Frequência                |
|:-------------------------:|:----------------------------:|:-------------------------:|:----------------------:|:------------------------------------:|
| antes do início do evento | sem registro                 | igual ao início do evento | igual ao fim do evento | [fim do evento] - [início do evento] |
| antes do início do evento | antes do início do evento    | igual à saída             | igual à saída          | [igual a zero]                       |
| antes do início do evento | entre início e fim do evento | igual ao início do evento | igual à saída          | [saída] - [início do evento]         |
| antes do início do evento | após o fim do evento         | igual ao início do evento | igual ao fim do evento | [fim do evento] - [início do evento] |
| após o início do evento   | sem registro                 | igual ao ingresso         | igual ao fim do evento | [fim do evento] - [ingresso]         |
| após o início do evento   | antes do fim do evento       | igual ao ingresso         | igual à saída          | [saída] - [ingresso]                 |
| após o início do evento   | após o fim do evento         | igual ao ingresso         | igual ao fim do evento | [fim do evento] - [ingresso]         |
| após o fim do evento      | sem registro                 | igual ao ingresso         | igual ao ingresso      | [igual a zero]                       |
| após o fim do evento      | após o fim do evento         | igual ao ingresso         | igual ao ingresso      | [igual a zero]                       |