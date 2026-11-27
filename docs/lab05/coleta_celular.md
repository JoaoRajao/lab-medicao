# Lab05 — Coleta em celulares (iPhone e Android)

Roda a coleta completa e o teste de concorrência no armazenamento real do celular. Os dois scripts usam só a biblioteca padrão do Python. Nenhum dado pessoal é coletado: o arquivo `*_ambiente.json` guarda só versões, sistema e processador.

| Teste | iPhone | Android | Por quê |
| --- | :---: | :---: | --- |
| Coleta completa (`coleta.py`) | ✅ | ✅ | Só Python e SQLite |
| Concorrência (`concorrencia.py --threads`) | ✅ | ✅ | O iOS não permite iniciar processos, então o escritor roda em uma *thread*. No Android usamos o mesmo modo, para os dois celulares serem comparáveis. No PC, os dois modos deram o mesmo padrão. |
| Durabilidade (queda de energia) | ❌ | ❌ | Nenhum dos dois permite derrubar o sistema sem acesso de administrador (root). A durabilidade foi medida só no Linux. |

**Antes de começar, nos dois:** celular **na tomada**, **bloqueio automático da tela desligado**, **economia de bateria desligada** e outros apps fechados. Não saia do app durante a coleta, porque o sistema pausa apps em segundo plano.

Digite **um comando por vez** e espere o cursor voltar antes do próximo.

## iPhone (app a-Shell, gratuito na App Store)

```
mkdir lab05
cd lab05
curl -L -o coleta.py https://raw.githubusercontent.com/JoaoRajao/lab-medicao/master/labs/lab05_sqlite/coleta.py
python3 coleta.py --repeticoes 30 --nome coleta_iphone
curl -L -o concorrencia.py https://raw.githubusercontent.com/JoaoRajao/lab-medicao/master/labs/lab05_sqlite/concorrencia.py
python3 concorrencia.py --threads --nome concorrencia_iphone
```

Os arquivos ficam em **Arquivos › No meu iPhone › a-Shell › lab05 › data › raw**.

## Android (app Termux)

Instale o Termux pelo **F-Droid** (f-droid.org) ou pela página oficial de versões (github.com/termux/termux-app/releases). A versão da Play Store pode estar desatualizada. O Android vai pedir para permitir a instalação de fora da loja; depois da coleta, o app pode ser desinstalado.

```
pkg update -y
pkg install -y python
termux-setup-storage
mkdir lab05
cd lab05
getprop ro.product.model > modelo.txt
getprop ro.build.version.release >> modelo.txt
curl -L -o coleta.py https://raw.githubusercontent.com/JoaoRajao/lab-medicao/master/labs/lab05_sqlite/coleta.py
python coleta.py --repeticoes 30 --nome coleta_android
curl -L -o concorrencia.py https://raw.githubusercontent.com/JoaoRajao/lab-medicao/master/labs/lab05_sqlite/concorrencia.py
python concorrencia.py --threads --nome concorrencia_android
cp data/raw/* modelo.txt ~/storage/downloads/
```

- `pkg update` pode fazer perguntas (`[Y/n]`): responda **Enter**.
- `termux-setup-storage` abre um pedido de permissão para acessar arquivos: toque em **Permitir**. É o que deixa copiar os resultados para a pasta Downloads no último comando.
- A coleta leva cerca de 5 min e a concorrência cerca de 15 min. Cada uma termina com uma linha `dados em …`.
- No fim, os 5 arquivos (`coleta_android.*`, `concorrencia_android.*` e `modelo.txt`) ficam na pasta **Downloads** do celular, prontos para enviar ao PC (Drive, e-mail ou WhatsApp como documento).

## Depois

Os arquivos vão para `labs/lab05_sqlite/data/raw/` sem edição. A coleta completa entra como mais um ambiente da replicação, e a concorrência como replicação de C-1 e C-2 (`python -m labs.lab05_sqlite.robustez`).
