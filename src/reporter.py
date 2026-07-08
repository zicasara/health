"""
Gerador de relatório genómico estruturado.

A partir do DataFrame de dados brutos já carregado pela GenomicETL,
produz um relatório com três secções:

    1. Sexo biológico inferido (a partir de chamadas nos cromossomas X/Y)
    2. Ancestralidade (marcadores informativos de ancestralidade, AIMs)
    3. Traços fenotípicos (pigmentação, metabolismo, etc.)

IMPORTANTE: este é um relatório de RASTREIO sobre dados de "chip" de
genotipagem (posições pré-selecionadas), não um diagnóstico clínico. As
interpretações são indicativas e seguem as convenções de orientação de
alelos do SNPedia / 23andMe. O genótipo detetado é sempre apresentado
para permitir verificação independente.
"""

# --- Marcadores Informativos de Ancestralidade (AIMs) ---------------------
AIMS_DATABASE = {
    "rs1426654":  {"gene": "SLC24A5",     "trait": "Pigmentação (alelo A fortemente selecionado em populações europeias)"},
    "rs3827760":  {"gene": "EDAR",        "trait": "Morfologia/glândulas (alelo G endémico na Ásia Oriental e Nativos Americanos)"},
    "rs12913832": {"gene": "OCA2/HERC2",  "trait": "Íris (alelo G recessivo associado a olhos claros)"},
    "rs2814778":  {"gene": "DARC",        "trait": "Antigénio Duffy (alelo C predominante em ancestralidade subsariana)"},
    "rs16891982": {"gene": "SLC45A2",     "trait": "Síntese de melanina (alelo G associado a linhagens caucásicas)"},
    "rs4988235":  {"gene": "MCM6/LCT",    "trait": "Tolerância à lactose (alelo T = mutação pastoralista indo-europeia)"},
    "rs671":      {"gene": "ALDH2",       "trait": "Metabolismo do álcool (alelo A quase exclusivo da Ásia Oriental)"},
    "rs1042602":  {"gene": "TYR",         "trait": "Pigmentação (variação de frequência europeia vs. não-europeia)"},
    "rs12203592": {"gene": "IRF4",        "trait": "Sardas/pigmentação clara (associado a fenótipos europeus)"},
    "rs1805007":  {"gene": "MC1R",        "trait": "Cabelo ruivo/pele clara (enriquecido no norte da Europa)"},
    "rs1800414":  {"gene": "OCA2",        "trait": "Pigmentação da pele (alta frequência na Ásia Oriental)"},
}

# --- Base de traços fenotípicos -------------------------------------------
# Para cada SNP: gene, traço, mapa genótipo->interpretação, e uma nota
# opcional (ex.: evidência fraca). Genótipos não listados caem numa mensagem
# genérica que mostra apenas o valor detetado.
TRAIT_DATABASE = {
    "rs4988235": {
        "gene": "MCM6 / LCT", "trait": "Tolerância à lactose",
        "genotypes": {
            "AA": "Persistência da lactase — tolerância à lactose provável",
            "AG": "Tolerância intermédia (portador)",
            "GA": "Tolerância intermédia (portador)",
            "GG": "Não-persistência da lactase — intolerância à lactose provável",
        },
    },
    "rs671": {
        "gene": "ALDH2", "trait": "Metabolismo do álcool / rubor",
        "genotypes": {
            "GG": "Enzima ALDH2 funcional — metabolismo normal, sem rubor típico",
            "GA": "Atividade reduzida — rubor e sensibilidade ao álcool",
            "AG": "Atividade reduzida — rubor e sensibilidade ao álcool",
            "AA": "Deficiência de ALDH2 — rubor intenso, forte intolerância ao álcool",
        },
    },
    "rs17822931": {
        "gene": "ABCC11", "trait": "Tipo de cerúmen e odor corporal",
        "genotypes": {
            "CC": "Cerúmen húmido; produção de odor corporal típica",
            "CT": "Cerúmen húmido (portador)",
            "TC": "Cerúmen húmido (portador)",
            "TT": "Cerúmen seco; odor corporal reduzido (comum na Ásia Oriental)",
        },
    },
    "rs1815739": {
        "gene": "ACTN3", "trait": "Tipo de fibra muscular (força vs. resistência)",
        "genotypes": {
            "CC": "α-actinina-3 funcional — perfil de força/velocidade (sprint)",
            "CT": "Perfil misto (força e resistência)",
            "TC": "Perfil misto (força e resistência)",
            "TT": "Ausência de α-actinina-3 — perfil de resistência",
        },
    },
    "rs12913832": {
        "gene": "HERC2 / OCA2", "trait": "Cor dos olhos",
        "genotypes": {
            "GG": "Olhos claros prováveis (azuis/verdes)",
            "AG": "Cor intermédia — provável castanho/verde",
            "GA": "Cor intermédia — provável castanho/verde",
            "AA": "Olhos escuros prováveis (castanhos)",
        },
    },
    "rs1805007": {
        "gene": "MC1R", "trait": "Cabelo ruivo / sensibilidade UV",
        "genotypes": {
            "CC": "Sem esta variante de cabelo ruivo (R151C)",
            "CT": "Portador de variante de cabelo ruivo (pele sensível ao sol)",
            "TC": "Portador de variante de cabelo ruivo (pele sensível ao sol)",
            "TT": "Duas cópias — cabelo ruivo e pele muito clara prováveis",
        },
    },
    "rs12203592": {
        "gene": "IRF4", "trait": "Sardas / cor do cabelo na infância",
        "genotypes": {
            "CC": "Menor propensão a sardas por este locus",
            "CT": "Propensão intermédia a sardas / cabelo mais claro",
            "TC": "Propensão intermédia a sardas / cabelo mais claro",
            "TT": "Maior propensão a sardas e pele clara",
        },
    },
    "rs16891982": {
        "gene": "SLC45A2", "trait": "Pigmentação da pele",
        "genotypes": {
            "GG": "Variante europeia — pele mais clara",
            "CG": "Pigmentação intermédia (portador)",
            "GC": "Pigmentação intermédia (portador)",
            "CC": "Variante ancestral — pele mais escura",
        },
    },
    "rs713598": {
        "gene": "TAS2R38", "trait": "Perceção do sabor amargo (PTC)",
        "genotypes": {
            "GG": "Provador de amargo (sensível a PTC)",
            "GC": "Sensibilidade intermédia ao amargo",
            "CG": "Sensibilidade intermédia ao amargo",
            "CC": "Não-provador provável (menor perceção de amargo)",
        },
        "note": "A perceção depende de um haplótipo de 3 SNPs; leitura indicativa.",
    },
    "rs4680": {
        "gene": "COMT", "trait": "Metabolismo de dopamina (Val158Met)",
        "genotypes": {
            "GG": "Val/Val — metabolização mais rápida de dopamina",
            "GA": "Val/Met — perfil intermédio",
            "AG": "Val/Met — perfil intermédio",
            "AA": "Met/Met — metabolização mais lenta",
        },
        "note": "Associações a personalidade/cognição são fracas e controversas.",
    },
}


class GenomicReport:
    """Produz um relatório estruturado a partir do DataFrame já carregado."""

    def __init__(self, data):
        if data is None:
            raise ValueError("Nenhum dado fornecido. Carregue os dados com GenomicETL.load_data() primeiro.")
        self.data = data
        # Índice rápido RSID -> genótipo (primeira ocorrência).
        self._genotype = dict(zip(data["RSID"], data["RESULT"]))

    # -- Secção 1: sexo biológico ------------------------------------------
    def infer_biological_sex(self):
        """Infere o sexo cromossómico a partir das chamadas em X e Y."""
        no_call = {"--", "", "NN"}
        chrom = self.data["CHROMOSOME"].astype(str).str.upper()

        y = self.data[chrom == "Y"]
        y_called = y[~y["RESULT"].isin(no_call)]
        y_total = len(y)
        y_rate = (len(y_called) / y_total) if y_total else 0.0

        x = self.data[chrom == "X"]
        x_called = x[~x["RESULT"].isin(no_call)]
        # Heterozigotia no X: dois alelos diferentes (típico de XX).
        het = x_called["RESULT"].apply(lambda g: len(str(g)) == 2 and g[0] != g[1])
        x_het_rate = (het.mean() if len(x_called) else 0.0)

        if y_rate >= 0.10:
            inferred = "XY (masculino)"
        elif y_total > 0:
            inferred = "XX (feminino)"
        else:
            inferred = "Indeterminado (sem sondas no Y)"

        return {
            "inferred": inferred,
            "y_total": y_total,
            "y_called": len(y_called),
            "y_call_rate": y_rate,
            "x_het_rate": x_het_rate,
        }

    # -- Secção 2: ancestralidade ------------------------------------------
    def analyze_ancestry(self):
        """Lista os AIMs presentes na amostra com o respetivo sinal populacional."""
        results = []
        for rsid, info in AIMS_DATABASE.items():
            genotype = self._genotype.get(rsid)
            if genotype and genotype not in {"--", ""}:
                results.append({
                    "rsid": rsid, "gene": info["gene"],
                    "genotype": genotype, "signal": info["trait"],
                })
        return results

    # -- Secção 3: traços fenotípicos --------------------------------------
    def analyze_traits(self):
        """Interpreta os SNPs de traços presentes na amostra."""
        results = []
        for rsid, info in TRAIT_DATABASE.items():
            genotype = self._genotype.get(rsid)
            if not genotype or genotype in {"--", ""}:
                continue
            interpretation = info["genotypes"].get(
                genotype, f"Genótipo {genotype} não catalogado — leitura manual necessária"
            )
            results.append({
                "rsid": rsid, "gene": info["gene"], "trait": info["trait"],
                "genotype": genotype, "interpretation": interpretation,
                "note": info.get("note"),
            })
        return results

    # -- Composição do relatório -------------------------------------------
    def generate_report(self, output_path=None):
        """Compõe o relatório em texto e, opcionalmente, grava-o em ficheiro."""
        sex = self.infer_biological_sex()
        ancestry = self.analyze_ancestry()
        traits = self.analyze_traits()

        lines = []
        add = lines.append
        add("=" * 68)
        add("RELATÓRIO GENÓMICO ESTRUTURADO")
        add("=" * 68)
        add(f"Variantes analisadas: {len(self.data):,}")
        add("")

        add("[1] SEXO BIOLÓGICO INFERIDO")
        add(f"    Resultado: {sex['inferred']}")
        add(f"    Cromossoma Y: {sex['y_called']}/{sex['y_total']} sondas com chamada "
            f"({sex['y_call_rate']*100:.1f}%)")
        add(f"    Heterozigotia no X: {sex['x_het_rate']*100:.1f}%")
        add("")

        add("[2] ANCESTRALIDADE (Marcadores AIMs presentes)")
        if not ancestry:
            add("    Nenhum marcador AIM catalogado presente na amostra.")
        for a in ancestry:
            add(f"    [{a['rsid']}] {a['gene']} | Genótipo: {a['genotype']}")
            add(f"        ↳ {a['signal']}")
        add("")

        add("[3] TRAÇOS FENOTÍPICOS")
        if not traits:
            add("    Nenhum SNP de traço catalogado presente na amostra.")
        for t in traits:
            add(f"    [{t['rsid']}] {t['gene']} — {t['trait']} | Genótipo: {t['genotype']}")
            add(f"        ↳ {t['interpretation']}")
            if t.get("note"):
                add(f"        ⚠ {t['note']}")
        add("")

        add("-" * 68)
        add("AVISO: Relatório de rastreio sobre dados de genotipagem por chip")
        add("(cobertura parcial do genoma). Interpretações indicativas, não")
        add("diagnósticas. Confirme qualquer achado relevante clinicamente.")
        add("=" * 68)

        report = "\n".join(lines)
        if output_path:
            with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(report + "\n")
        return report
