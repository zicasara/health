import pandas as pd

FILE_PATH = 'data/dados_brutos20260707.csv.gz'

AIMS_DATABASE = {
    'rs1426654': {'gene': 'SLC24A5', 'trait': 'Pigmentação (Alelo A fortemente selecionado em populações europeias)'},
    'rs3827760': {'gene': 'EDAR', 'trait': 'Morfologia e glândulas (Alelo G endémico na Ásia Oriental e Nativos Americanos)'},
    'rs12913832': {'gene': 'OCA2/HERC2', 'trait': 'Íris (Alelo G recessivo associado a fenótipos de olhos claros)'},
    'rs2814778': {'gene': 'DARC', 'trait': 'Antigénio Duffy (Alelo C predominante em ancestralidade subsaariana profunda)'},
    'rs16891982': {'gene': 'SLC45A2', 'trait': 'Síntese de melanina (Alelo G associado a linhagens caucásicas)'},
    'rs4988235': {'gene': 'MCM6 / LCT', 'trait': 'Tolerância à Lactose (Alelo T sinaliza mutação pastoralista indo-europeia)'}
}

def decode_ancestry(file_path):
    print(f"A inicializar o motor de processamento genómico para: {file_path}\n")

    try:
        df = pd.read_csv(file_path, compression='gzip' if file_path.endswith('.gz') else 'infer')
        df.columns = [col.strip().upper() for col in df.columns]

        if 'RSID' not in df.columns or 'RESULT' not in df.columns:
            raise ValueError("Falha na integridade estrutural: Colunas RSID ou RESULT ausentes.")

        aims_keys = list(AIMS_DATABASE.keys())
        user_aims = df[df['RSID'].isin(aims_keys)]

        print("=== RELATÓRIO DE MARCADORES DE ANCESTRALIDADE (AIMs) ===")
        if user_aims.empty:
            print("Nenhum dos marcadores AIM listados foi identificado na matriz atual.")
        else:
            for _, row in user_aims.iterrows():
                rsid = row['RSID']
                genotype = row['RESULT']
                info = AIMS_DATABASE[rsid]
                print(f"[{rsid}] Locus {info['gene']} | Genótipo Detetado: {genotype}")
                print(f" ↳ Filogenia: {info['trait']}\n")

        if 'CHROMOSOME' in df.columns:
            mtdna = df[df['CHROMOSOME'].astype(str).isin(['MT', '26', 'M'])]

            print("=== MATRIZ MITOCONDRIAL (LINHAGEM MATERNA) ===")
            print(f"Extraídos {len(mtdna)} SNPs do genoma mitocondrial absoluto.")

            if not mtdna.empty:
                print("Amostra dos 5 loci basais para rastreio de Haplogrupo:")
                print(mtdna[['RSID', 'POSITION', 'RESULT']].head().to_string(index=False))
                print("\n[Nota Estratégica]: Pode exportar este subset mitocondrial e inseri-lo num interpretador de haplogrupos open-source (ex: James Lick's mtHap) para traçar a rota paleolítica da sua linhagem feminina.")

    except FileNotFoundError:
        print("Exceção IO: O ficheiro não foi encontrado no diretório de execução atual.")
    except Exception as e:
        print(f"Interrupção do processamento: {e}")

if __name__ == "__main__":
    decode_ancestry(FILE_PATH)
