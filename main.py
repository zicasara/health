import argparse
from src.parser import GenomicETL


def main():
    parser = argparse.ArgumentParser(description="Pipeline de conversão de dados genómicos brutos (mtDNA).")
    parser.add_argument("-i", "--input", required=True, help="Caminho para o ficheiro de dados brutos (.csv, .txt, .gz)")
    parser.add_argument("-o", "--output", required=True, help="Caminho para o ficheiro de saída limpo (.txt)")
    parser.add_argument(
        "-r", "--report",
        help="(Opcional) Caminho para gravar o relatório estruturado "
             "(sexo inferido, ancestralidade e traços). Use '-' para imprimir no ecrã.",
    )

    args = parser.parse_args()

    # Execução do Pipeline
    etl = GenomicETL(file_path=args.input)
    etl.load_data()
    etl.filter_mitochondrial_dna()
    etl.export_mthap_format(output_path=args.output)

    # Relatório estruturado opcional
    if args.report:
        if args.report == "-":
            print("\n" + etl.generate_report())
        else:
            etl.generate_report(output_path=args.report)


if __name__ == "__main__":
    main()
