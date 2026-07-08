import argparse
from src.parser import GenomicETL


def main():
    parser = argparse.ArgumentParser(description="Pipeline de conversão de dados genómicos brutos (mtDNA).")
    parser.add_argument("-i", "--input", required=True, help="Caminho para o ficheiro de dados brutos (.csv, .txt, .gz)")
    parser.add_argument("-o", "--output", required=True, help="Caminho para o ficheiro de saída limpo (.txt)")

    args = parser.parse_args()

    # Execução do Pipeline
    etl = GenomicETL(file_path=args.input)
    etl.load_data()
    etl.filter_mitochondrial_dna()
    etl.export_mthap_format(output_path=args.output)


if __name__ == "__main__":
    main()
