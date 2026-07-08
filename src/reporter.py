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

# --- Predisposições de saúde (RASTREIO, não diagnóstico) ------------------
# Cada entrada: categoria, gene, condição, mapa genótipo->interpretação,
# nível de evidência e nota. Os mapas seguem a orientação de alelos do
# dbSNP/23andMe; genótipos não catalogados caem numa mensagem neutra que
# apenas mostra o valor detetado (nunca inventa um risco).
#
# AVISO CLÍNICO: nenhuma destas leituras substitui teste clínico ou
# aconselhamento genético. Um chip cobre posições pré-definidas — a
# ausência de uma variante NÃO garante a sua ausência no genoma.
HEALTH_DATABASE = {
    # -- Predisposição a doença (multifatorial) --
    "rs7903146": {
        "category": "Predisposição a doença", "gene": "TCF7L2",
        "condition": "Diabetes tipo 2", "evidence": "forte",
        "genotypes": {
            "CC": "Sem alelo de risco — risco genético mais baixo neste locus",
            "CT": "Um alelo de risco — risco moderadamente aumentado",
            "TC": "Um alelo de risco — risco moderadamente aumentado",
            "TT": "Dois alelos de risco — risco aumentado",
        },
        "note": "Risco poligénico e fortemente modulado por estilo de vida.",
    },
    "rs1061170": {
        "category": "Predisposição a doença", "gene": "CFH (Y402H)",
        "condition": "Degenerescência macular da idade (DMI)", "evidence": "forte",
        "genotypes": {
            "TT": "Sem alelo de risco",
            "CT": "Um alelo de risco de DMI",
            "TC": "Um alelo de risco de DMI",
            "CC": "Dois alelos de risco — risco aumentado de DMI",
        },
        "note": "Risco reduzível: não fumar, proteção UV e dieta/suplementos AREDS.",
    },
    "rs10490924": {
        "category": "Predisposição a doença", "gene": "ARMS2",
        "condition": "Degenerescência macular da idade (DMI)", "evidence": "forte",
        "genotypes": {
            "GG": "Sem alelo de risco ARMS2",
            "GT": "Um alelo de risco", "TG": "Um alelo de risco",
            "TT": "Dois alelos de risco",
        },
    },
    "rs2187668": {
        "category": "Predisposição a doença", "gene": "HLA-DQ2.5",
        "condition": "Doença celíaca (suscetibilidade)", "evidence": "forte",
        "genotypes": {
            "CC": "Tag DQ2.5 ausente — risco genético baixo (DQ8 não avaliado por este marcador)",
            "CT": "Portador do haplótipo DQ2.5",
            "TC": "Portador do haplótipo DQ2.5",
            "TT": "Homozigoto DQ2.5",
        },
        "note": "A maioria dos portadores de DQ2.5 NUNCA desenvolve a doença.",
    },
    "rs34637584": {
        "category": "Predisposição a doença", "gene": "LRRK2 (G2019S)",
        "condition": "Doença de Parkinson", "evidence": "forte (variante específica)",
        "genotypes": {
            "GG": "Sem a variante G2019S",
            "GA": "Portador de G2019S — risco aumentado",
            "AG": "Portador de G2019S — risco aumentado",
            "AA": "Homozigoto G2019S",
        },
        "note": "Cobre apenas a variante G2019S, não todo o risco de Parkinson.",
    },

    # -- Trombofilia / estado de portador --
    "rs6025": {
        "category": "Trombofilia / portador", "gene": "F5 (Fator V Leiden)",
        "condition": "Trombofilia hereditária", "evidence": "forte",
        "genotypes": {
            "CC": "Sem a variante Fator V Leiden — risco não aumentado por este locus",
            "CT": "Portador de Fator V Leiden — risco de trombose aumentado",
            "TC": "Portador de Fator V Leiden — risco de trombose aumentado",
            "TT": "Homozigoto — risco de trombose elevado",
        },
    },
    "rs1799963": {
        "category": "Trombofilia / portador", "gene": "F2 (protrombina G20210A)",
        "condition": "Trombofilia hereditária", "evidence": "forte",
        "genotypes": {
            "GG": "Sem a variante G20210A",
            "GA": "Portador de G20210A — risco de trombose aumentado",
            "AG": "Portador de G20210A — risco de trombose aumentado",
            "AA": "Homozigoto",
        },
    },
    "rs1800562": {
        "category": "Trombofilia / portador", "gene": "HFE (C282Y)",
        "condition": "Hemocromatose hereditária", "evidence": "forte",
        "genotypes": {
            "GG": "Sem a variante C282Y",
            "GA": "Portador de C282Y", "AG": "Portador de C282Y",
            "AA": "Homozigoto C282Y — principal genótipo de risco de hemocromatose",
        },
        "note": "O risco clínico depende da combinação C282Y/H63D (ver abaixo).",
    },
    "rs1799945": {
        "category": "Trombofilia / portador", "gene": "HFE (H63D)",
        "condition": "Hemocromatose hereditária", "evidence": "moderada",
        "genotypes": {
            "CC": "Sem a variante H63D",
            "CG": "Portador de H63D (baixa penetrância)",
            "GC": "Portador de H63D (baixa penetrância)",
            "GG": "Homozigoto H63D",
        },
    },
    "rs28929474": {
        "category": "Trombofilia / portador", "gene": "SERPINA1 (PiZ)",
        "condition": "Deficiência de alfa-1-antitripsina", "evidence": "forte",
        "genotypes": {
            "CC": "Sem o alelo Z",
            "CT": "Portador PiZ", "TC": "Portador PiZ",
            "TT": "ZZ — deficiência de alfa-1-antitripsina",
        },
    },
    "rs17580": {
        "category": "Trombofilia / portador", "gene": "SERPINA1 (PiS)",
        "condition": "Deficiência de alfa-1-antitripsina", "evidence": "forte",
        "genotypes": {
            "TT": "Sem o alelo S",
            "TA": "Portador PiS", "AT": "Portador PiS",
            "AA": "SS",
        },
    },
    "rs1801133": {
        "category": "Trombofilia / portador", "gene": "MTHFR (C677T)",
        "condition": "Metabolismo do folato", "evidence": "fraca",
        "genotypes": {
            "GG": "Sem a variante C677T — atividade normal",
            "GA": "Heterozigoto C677T — atividade ligeiramente reduzida (comum)",
            "AG": "Heterozigoto C677T — atividade ligeiramente reduzida (comum)",
            "AA": "Homozigoto C677T — atividade reduzida (~30%)",
        },
        "note": "Sociedades médicas (ex.: ACMG) NÃO recomendam o teste de MTHFR "
                "para trombofilia; achado geralmente sem significado clínico.",
    },
    "rs1801131": {
        "category": "Trombofilia / portador", "gene": "MTHFR (A1298C)",
        "condition": "Metabolismo do folato", "evidence": "fraca",
        "genotypes": {
            "TT": "Sem a variante A1298C",
            "TG": "Heterozigoto A1298C", "GT": "Heterozigoto A1298C",
            "GG": "Homozigoto A1298C",
        },
    },
    "rs887829": {
        "category": "Trombofilia / portador", "gene": "UGT1A1",
        "condition": "Síndrome de Gilbert (benigna)", "evidence": "forte",
        "genotypes": {
            "CC": "Sem a variante",
            "CT": "Portador — síndrome de Gilbert improvável (requer homozigotia)",
            "TC": "Portador — síndrome de Gilbert improvável (requer homozigotia)",
            "TT": "Homozigoto — compatível com síndrome de Gilbert (benigna)",
        },
    },

    # -- Farmacogenética --
    "rs4149056": {
        "category": "Farmacogenética", "gene": "SLCO1B1",
        "condition": "Miopatia induzida por estatinas", "evidence": "forte",
        "genotypes": {
            "TT": "Função normal do transportador",
            "TC": "Função reduzida — risco intermédio de miopatia (esp. sinvastatina)",
            "CT": "Função reduzida — risco intermédio de miopatia (esp. sinvastatina)",
            "CC": "Função baixa — risco elevado de miopatia por estatinas",
        },
    },
    "rs9923231": {
        "category": "Farmacogenética", "gene": "VKORC1",
        "condition": "Sensibilidade à varfarina", "evidence": "forte",
        "genotypes": {
            "CC": "Sensibilidade normal à varfarina",
            "CT": "Sensibilidade intermédia — possível dose mais baixa",
            "TC": "Sensibilidade intermédia — possível dose mais baixa",
            "TT": "Alta sensibilidade — dose baixa",
        },
    },
    "rs1799853": {
        "category": "Farmacogenética", "gene": "CYP2C9*2",
        "condition": "Metabolismo de varfarina/AINEs", "evidence": "forte",
        "genotypes": {
            "CC": "Sem alelo *2 — metabolismo normal",
            "CT": "Portador *2 — metabolismo reduzido", "TC": "Portador *2 — metabolismo reduzido",
            "TT": "*2/*2 — metabolismo lento",
        },
    },
    "rs1057910": {
        "category": "Farmacogenética", "gene": "CYP2C9*3",
        "condition": "Metabolismo de varfarina/AINEs", "evidence": "forte",
        "genotypes": {
            "AA": "Sem alelo *3 — metabolismo normal",
            "AC": "Portador *3 — metabolismo reduzido", "CA": "Portador *3 — metabolismo reduzido",
            "CC": "*3/*3 — metabolismo lento",
        },
    },
    "rs762551": {
        "category": "Farmacogenética", "gene": "CYP1A2",
        "condition": "Metabolismo da cafeína", "evidence": "moderada",
        "genotypes": {
            "AA": "Metabolizador rápido de cafeína",
            "AC": "Metabolizador intermédio", "CA": "Metabolizador intermédio",
            "CC": "Metabolizador lento",
        },
    },

    # -- Estilo de vida --
    "rs16969968": {
        "category": "Estilo de vida", "gene": "CHRNA5",
        "condition": "Dependência de nicotina", "evidence": "forte",
        "genotypes": {
            "GG": "Sem alelo de risco",
            "GA": "Um alelo — maior dependência de nicotina se fumar",
            "AG": "Um alelo — maior dependência de nicotina se fumar",
            "AA": "Dois alelos — dependência acentuada e maior risco de cancro do pulmão se fumar",
        },
        "note": "Relevante apenas em contexto de tabagismo.",
    },
}


def _lookup_genotype(genotype, mapping):
    """Procura o genótipo no mapa, tolerando a ordem dos alelos (CT == TC)."""
    if genotype in mapping:
        return mapping[genotype]
    if len(genotype) == 2 and genotype[::-1] in mapping:
        return mapping[genotype[::-1]]
    return None


def resolve_apoe(g429358, g7412):
    """
    Determina o genótipo APOE (ε2/ε3/ε4) a partir de rs429358 e rs7412.

    Cada haplótipo é definido pelo par de bases nas duas posições:
        ε2 = (T, T) | ε3 = (T, C) | ε4 = (C, C)
    Requer ambos os SNPs com chamada de 2 alelos.
    """
    if not g429358 or not g7412 or len(g429358) != 2 or len(g7412) != 2:
        return None
    haplo = {("T", "T"): "ε2", ("T", "C"): "ε3", ("C", "C"): "ε4"}
    # Empareja as duas ordenações possíveis dos alelos e escolhe a que
    # produz dois haplótipos válidos.
    for a1, a2 in ((g429358[0], g429358[1]), (g429358[1], g429358[0])):
        alleles = (haplo.get((a1, g7412[0])), haplo.get((a2, g7412[1])))
        if all(alleles):
            e1, e2 = sorted(alleles)  # ordem canónica (ε2<ε3<ε4)
            return f"{e1}/{e2}"
    return None

# Interpretação e risco por genótipo APOE (foco em Alzheimer de início tardio).
APOE_INTERPRETATION = {
    "ε2/ε2": "Risco reduzido de Alzheimer; possível efeito na lipidémia",
    "ε2/ε3": "Risco de Alzheimer ligeiramente reduzido",
    "ε2/ε4": "Efeitos opostos combinados — risco próximo do médio",
    "ε3/ε3": "Genótipo mais comum — risco de referência (médio)",
    "ε3/ε4": "Uma cópia ε4 — risco de Alzheimer aumentado (~2-3×) e LDL mais alto",
    "ε4/ε4": "Duas cópias ε4 — risco de Alzheimer substancialmente aumentado",
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

    # -- Secção 4: predisposições de saúde ---------------------------------
    def analyze_health(self):
        """
        Avalia marcadores de predisposição de saúde presentes na amostra.

        RASTREIO, não diagnóstico. Devolve uma lista de dicionários,
        incluindo o resultado composto de APOE quando disponível.
        """
        results = []

        # APOE precisa de dois SNPs combinados.
        apoe = resolve_apoe(self._genotype.get("rs429358"), self._genotype.get("rs7412"))
        if apoe:
            results.append({
                "category": "Predisposição a doença", "gene": "APOE",
                "condition": "Alzheimer de início tardio / lipidémia",
                "genotype": apoe, "evidence": "forte",
                "interpretation": APOE_INTERPRETATION.get(apoe, "Genótipo APOE detetado"),
                "note": "Fator de risco, NÃO determinístico; a maioria com ε4 não "
                        "desenvolve Alzheimer. Considere aconselhamento genético.",
            })

        for rsid, info in HEALTH_DATABASE.items():
            genotype = self._genotype.get(rsid)
            if not genotype or genotype in {"--", ""}:
                continue
            interpretation = _lookup_genotype(genotype, info["genotypes"])
            if interpretation is None:
                interpretation = f"Genótipo {genotype} não catalogado — leitura manual necessária"
            results.append({
                "category": info["category"], "gene": info["gene"],
                "condition": info["condition"], "genotype": genotype,
                "evidence": info.get("evidence", ""),
                "interpretation": interpretation, "note": info.get("note"),
            })

        # Ordena por categoria (ordem estável definida) para leitura coerente.
        order = ["Predisposição a doença", "Trombofilia / portador",
                 "Farmacogenética", "Estilo de vida"]
        results.sort(key=lambda r: order.index(r["category"]) if r["category"] in order else 99)
        return results

    # -- Composição do relatório -------------------------------------------
    def generate_report(self, output_path=None, fmt="text"):
        """
        Compõe o relatório e, opcionalmente, grava-o em ficheiro.

        fmt: "text" (predefinição) ou "markdown"/"md".
        """
        if fmt in ("markdown", "md"):
            report = self._render_markdown()
        else:
            report = self._render_text()

        if output_path:
            with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(report + "\n")
        return report

    def _render_text(self):
        """Compõe o relatório em texto simples."""
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

        health = self.analyze_health()
        add("[4] PREDISPOSIÇÕES DE SAÚDE (rastreio, não diagnóstico)")
        if not health:
            add("    Nenhum marcador de saúde catalogado presente na amostra.")
        current = None
        for h in health:
            if h["category"] != current:
                current = h["category"]
                add(f"  -- {current} --")
            evid = f" [evidência: {h['evidence']}]" if h.get("evidence") else ""
            add(f"    [{h['gene']}] {h['condition']} | Genótipo: {h['genotype']}{evid}")
            add(f"        ↳ {h['interpretation']}")
            if h.get("note"):
                add(f"        ⚠ {h['note']}")
        add("")

        add("-" * 68)
        add("AVISO: Relatório de RASTREIO sobre dados de genotipagem por chip")
        add("(cobertura parcial do genoma). Interpretações indicativas, NÃO")
        add("diagnósticas — a ausência de uma variante não garante a sua")
        add("ausência no genoma. Não tome decisões médicas com base neste")
        add("relatório; procure confirmação clínica e aconselhamento genético.")
        add("=" * 68)

        return "\n".join(lines)

    def _render_markdown(self):
        """Compõe o relatório em Markdown."""
        sex = self.infer_biological_sex()
        ancestry = self.analyze_ancestry()
        traits = self.analyze_traits()

        lines = []
        add = lines.append
        add("# Relatório Genómico Estruturado")
        add("")
        add(f"**Variantes analisadas:** {len(self.data):,}")
        add("")

        add("## 1. Sexo biológico inferido")
        add("")
        add(f"- **Resultado:** {sex['inferred']}")
        add(f"- **Cromossoma Y:** {sex['y_called']}/{sex['y_total']} sondas com chamada "
            f"({sex['y_call_rate']*100:.1f}%)")
        add(f"- **Heterozigotia no X:** {sex['x_het_rate']*100:.1f}%")
        add("")

        add("## 2. Ancestralidade (marcadores AIMs presentes)")
        add("")
        if not ancestry:
            add("_Nenhum marcador AIM catalogado presente na amostra._")
        else:
            add("| RSID | Gene | Genótipo | Sinal populacional |")
            add("|------|------|:--------:|--------------------|")
            for a in ancestry:
                add(f"| `{a['rsid']}` | {a['gene']} | `{a['genotype']}` | {a['signal']} |")
        add("")

        add("## 3. Traços fenotípicos")
        add("")
        if not traits:
            add("_Nenhum SNP de traço catalogado presente na amostra._")
        else:
            add("| RSID | Gene | Traço | Genótipo | Interpretação |")
            add("|------|------|-------|:--------:|---------------|")
            for t in traits:
                interp = t["interpretation"]
                if t.get("note"):
                    interp += f" ⚠️ _{t['note']}_"
                add(f"| `{t['rsid']}` | {t['gene']} | {t['trait']} | `{t['genotype']}` | {interp} |")
        add("")

        health = self.analyze_health()
        add("## 4. Predisposições de saúde (rastreio, não diagnóstico)")
        add("")
        if not health:
            add("_Nenhum marcador de saúde catalogado presente na amostra._")
        else:
            current = None
            for i, h in enumerate(health):
                if h["category"] != current:
                    current = h["category"]
                    add(f"### {current}")
                    add("")
                    add("| RSID/Gene | Condição | Genótipo | Evidência | Interpretação |")
                    add("|-----------|----------|:--------:|:---------:|---------------|")
                interp = h["interpretation"]
                if h.get("note"):
                    interp += f" ⚠️ _{h['note']}_"
                add(f"| {h['gene']} | {h['condition']} | `{h['genotype']}` "
                    f"| {h.get('evidence','')} | {interp} |")
                # Linha em branco antes de iniciar uma nova categoria.
                nxt = health[i + 1] if i + 1 < len(health) else None
                if nxt and nxt["category"] != current:
                    add("")
        add("")

        add("---")
        add("")
        add("> **Aviso:** Relatório de **rastreio** sobre dados de genotipagem por chip "
            "(cobertura parcial do genoma). As interpretações são indicativas e **não "
            "diagnósticas** — a ausência de uma variante não garante a sua ausência no "
            "genoma. Não tome decisões médicas com base neste relatório; para qualquer "
            "achado relevante procure confirmação clínica e aconselhamento genético.")

        return "\n".join(lines)
