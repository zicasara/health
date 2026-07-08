"""
Motor de ETL (Extract, Transform, Load) para dados genómicos brutos.

Converte ficheiros de genotipagem no formato de "chip" comercial
(23andMe / AncestryDNA / FamilyTreeDNA) num subset mitocondrial (mtDNA)
pronto a ser interpretado por ferramentas de haplogrupos como o
mtHap de James Lick (https://dna.jameslick.com/mthap/).
"""

import pandas as pd

from .reporter import GenomicReport

# Identificadores usados por diferentes fabricantes para o cromossoma mitocondrial.
MITO_CHROMOSOME_LABELS = {"MT", "M", "26", "CHRM", "MITO"}

# Colunas esperadas no ficheiro bruto, após normalização.
REQUIRED_COLUMNS = ("RSID", "CHROMOSOME", "POSITION", "RESULT")


def _split_alleles(result):
    """
    Converte um genótipo (ex.: "GG", "CA", "G", "II", "--") no par de
    alelos do formato AncestryDNA. Chamadas em falta -> ("0", "0").
    """
    g = str(result).strip().upper()
    if g in ("--", "", "NN", "00", "-"):
        return ("0", "0")
    if len(g) == 1:               # haploide (MT/Y) -> alelo duplicado
        return (g, g)
    a1 = g[0] if g[0] != "-" else "0"
    a2 = g[1] if g[1] != "-" else "0"
    return (a1, a2)


class GenomicETL:
    """Pipeline de extração e conversão de dados genómicos brutos."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None          # DataFrame completo carregado
        self.mtdna = None         # Subset mitocondrial após filtragem

    def load_data(self):
        """Carrega o ficheiro bruto e normaliza a estrutura das colunas."""
        print(f"[1/3] A carregar dados brutos de: {self.file_path}")

        compression = "gzip" if str(self.file_path).endswith(".gz") else "infer"
        df = pd.read_csv(
            self.file_path,
            compression=compression,
            dtype=str,
            comment="#",
        )

        # Normaliza cabeçalhos (remove espaços, uniformiza maiúsculas).
        df.columns = [col.strip().upper() for col in df.columns]

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                "Falha na integridade estrutural. Colunas em falta: "
                + ", ".join(missing)
            )

        # Limpa espaços em branco residuais nos valores.
        for col in REQUIRED_COLUMNS:
            df[col] = df[col].astype(str).str.strip()

        self.data = df
        print(f"      {len(df):,} variantes carregadas com sucesso.")
        return self.data

    def filter_mitochondrial_dna(self):
        """Extrai apenas as variantes do genoma mitocondrial (linhagem materna)."""
        if self.data is None:
            raise RuntimeError("Os dados ainda não foram carregados. Chame load_data() primeiro.")

        print("[2/3] A filtrar variantes mitocondriais (mtDNA)...")

        chrom = self.data["CHROMOSOME"].astype(str).str.strip().str.upper()
        mask = chrom.isin(MITO_CHROMOSOME_LABELS)
        mtdna = self.data[mask].copy()

        # Ordena por posição numérica (rCRS) para uma leitura coerente.
        mtdna["_POS_INT"] = pd.to_numeric(mtdna["POSITION"], errors="coerce")
        mtdna = mtdna.sort_values("_POS_INT", kind="stable").drop(columns="_POS_INT")

        self.mtdna = mtdna
        print(f"      {len(mtdna):,} SNPs mitocondriais isolados.")
        if mtdna.empty:
            print("      [Aviso] Nenhuma variante mitocondrial encontrada na matriz.")
        return self.mtdna

    def export_mthap_format(self, output_path):
        """
        Exporta o subset mitocondrial no formato bruto tipo 23andMe,
        aceite diretamente pelo interpretador de haplogrupos mtHap.

        Formato (separado por tabulações):
            rsid    chromosome    position    genotype
        """
        if self.mtdna is None:
            raise RuntimeError(
                "O subset mitocondrial não existe. Chame filter_mitochondrial_dna() primeiro."
            )

        print(f"[3/3] A exportar formato mtHap para: {output_path}")

        export_df = self.mtdna[list(REQUIRED_COLUMNS)].copy()
        # mtHap usa "MT" como identificador canónico do cromossoma mitocondrial.
        export_df["CHROMOSOME"] = "MT"

        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("# rsid\tchromosome\tposition\tgenotype\n")
            for _, row in export_df.iterrows():
                handle.write(
                    f"{row['RSID']}\t{row['CHROMOSOME']}\t{row['POSITION']}\t{row['RESULT']}\n"
                )

        print(f"      Exportação concluída: {len(export_df):,} linhas escritas.")
        print(
            "      Carregue este ficheiro em https://dna.jameslick.com/mthap/ "
            "para estimar o seu haplogrupo materno."
        )
        return output_path

    def export_gedmatch_format(self, output_path):
        """
        Exporta o genoma completo no formato bruto tipo 23andMe, aceite
        pelo GEDmatch (Build 37/GRCh37 — ver validação no README).

        Formato (separado por tabulações, ordenado por cromossoma e posição):
            rsid    chromosome    position    genotype
        """
        if self.data is None:
            raise RuntimeError("Os dados ainda não foram carregados. Chame load_data() primeiro.")

        print(f"[+] A exportar formato GEDmatch (23andMe) para: {output_path}")

        export_df = self.data[list(REQUIRED_COLUMNS)].copy()

        # Ordena por cromossoma (1-22, X, Y, MT) e depois por posição numérica.
        chrom_order = {str(i): i for i in range(1, 23)}
        chrom_order.update({"X": 23, "Y": 24, "MT": 25, "M": 25})
        export_df["_C"] = export_df["CHROMOSOME"].str.upper().map(chrom_order).fillna(99)
        export_df["_P"] = pd.to_numeric(export_df["POSITION"], errors="coerce")
        export_df = export_df.sort_values(["_C", "_P"], kind="stable")

        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            # Cabeçalho no estilo 23andMe (Build 37). GEDmatch deteta este layout.
            handle.write("# Dados de genótipo bruto exportados para carregamento no GEDmatch.\n")
            handle.write("# Assembly: GRCh37/hg19 (Build 37).\n")
            handle.write("# rsid\tchromosome\tposition\tgenotype\n")
            for _, row in export_df.iterrows():
                handle.write(
                    f"{row['RSID']}\t{row['CHROMOSOME']}\t{row['POSITION']}\t{row['RESULT']}\n"
                )

        print(f"    Exportação concluída: {len(export_df):,} variantes (genoma completo).")
        print("    Carregue este ficheiro (ou a versão .gz) em https://www.gedmatch.com/")
        return output_path

    def export_ancestrydna_format(self, output_path):
        """
        Exporta o genoma completo no formato bruto do AncestryDNA (Build 37):
        5 colunas separadas por tabulações, com os dois alelos em colunas
        distintas e cromossomas em código numérico (X=23, Y=24, MT=26).

            rsid    chromosome    position    allele1    allele2
        """
        if self.data is None:
            raise RuntimeError("Os dados ainda não foram carregados. Chame load_data() primeiro.")

        print(f"[+] A exportar formato AncestryDNA para: {output_path}")

        export_df = self.data[list(REQUIRED_COLUMNS)].copy()

        # Código numérico de cromossoma usado pelo AncestryDNA.
        chrom_map = {str(i): str(i) for i in range(1, 23)}
        chrom_map.update({"X": "23", "Y": "24", "MT": "26", "M": "26"})
        chrom_sort = {str(i): i for i in range(1, 23)}
        chrom_sort.update({"X": 23, "Y": 24, "MT": 26, "M": 26})

        export_df["_C"] = export_df["CHROMOSOME"].str.upper().map(chrom_sort).fillna(99)
        export_df["_P"] = pd.to_numeric(export_df["POSITION"], errors="coerce")
        export_df = export_df.sort_values(["_C", "_P"], kind="stable")

        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#AncestryDNA raw data download\n")
            handle.write("#Dados de genótipo bruto convertidos para o formato AncestryDNA.\n")
            handle.write("#Assembly: GRCh37/hg19 (Build 37).\n")
            # Cabeçalho (linha NÃO comentada) que o GEDmatch usa para detetar o formato.
            handle.write("rsid\tchromosome\tposition\tallele1\tallele2\n")
            for _, row in export_df.iterrows():
                chrom = chrom_map.get(str(row["CHROMOSOME"]).upper(), str(row["CHROMOSOME"]))
                a1, a2 = _split_alleles(row["RESULT"])
                handle.write(f"{row['RSID']}\t{chrom}\t{row['POSITION']}\t{a1}\t{a2}\n")

        print(f"    Exportação concluída: {len(export_df):,} variantes (genoma completo).")
        print("    Carregue este ficheiro (ou a versão .gz) em https://www.gedmatch.com/")
        return output_path

    def generate_report(self, output_path=None, fmt=None):
        """
        Gera um relatório estruturado (sexo inferido, ancestralidade e
        traços fenotípicos) a partir dos dados carregados.

        fmt: "text" ou "markdown". Se None, é inferido pela extensão do
        ficheiro de saída (.md/.markdown -> markdown), caindo em "text".
        """
        if self.data is None:
            raise RuntimeError("Os dados ainda não foram carregados. Chame load_data() primeiro.")

        if fmt is None:
            path = str(output_path or "").lower()
            fmt = "markdown" if path.endswith((".md", ".markdown")) else "text"

        print("[+] A gerar relatório genómico estruturado...")
        report = GenomicReport(self.data).generate_report(output_path=output_path, fmt=fmt)
        if output_path:
            print(f"    Relatório ({fmt}) gravado em: {output_path}")
        return report
