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

# ==========================================================================
# SECÇÃO 5: ANCESTRALIDADE & FENÓTIPO GLOBAL
# ==========================================================================

# --- (a) Predição de pigmentação (subconjunto do painel HIrisPlex-S) ------
# Modelo direcional simplificado: cada traço é decidido pelos SNPs de maior
# efeito presentes no chip. NÃO é a probabilidade forense validada (que exige
# os 41 SNPs e coeficientes do modelo multinomial), mas segue a mesma direção.
PIGMENT_EYE = {  # rs12913832 (HERC2) — preditor dominante da cor dos olhos
    "GG": "Olhos claros prováveis (azul/verde)",
    "AG": "Cor intermédia — provável castanho/avelã",
    "GA": "Cor intermédia — provável castanho/avelã",
    "AA": "Olhos escuros prováveis (castanho)",
}
PIGMENT_SKIN = {  # rs16891982 (SLC45A2) — forte preditor da tonalidade da pele
    "GG": "Pele clara (típico europeu)",
    "CG": "Pele intermédia",
    "GC": "Pele intermédia",
    "CC": "Pele mais escura",
}
# Marcadores completos do painel HIrisPlex-S (para calcular a cobertura).
HIRISPLEX_PANEL = [
    "rs312262906","rs11547464","rs885479","rs1805008","rs1805005","rs1805006",
    "rs1805007","rs1805009","rs201326893","rs2228479","rs1110400","rs28777",
    "rs16891982","rs12821256","rs4959270","rs12203592","rs1042602","rs1800407",
    "rs2402130","rs12913832","rs2378249","rs12896399","rs1393350","rs683",
    "rs3114908","rs1800414","rs10756819","rs2238289","rs17128291","rs6497292",
    "rs1129038","rs1667394","rs1126809","rs1470608","rs1426654","rs17422",
    "rs6119471","rs1545397","rs8051733","rs2069945","rs1015362",
]

# --- (b) Rastreio da linhagem materna (mtDNA, exclusionário) ---------------
# Posição rCRS -> (alelo derivado, macro-linhagem, significado). Só usamos
# posições com base limpa (A/C/G/T). Concebido para EXCLUIR linhagens, não
# para atribuir um haplogrupo definitivo (isso é tarefa do mtHap).
MT_LINEAGE_MARKERS = [
    {"pos": 663,   "derived": "G", "lineage": "A (ameríndio/asiático)"},
    {"pos": 1736,  "derived": "G", "lineage": "A (ameríndio/asiático)"},
    {"pos": 13263, "derived": "G", "lineage": "C (ameríndio)"},
    {"pos": 5178,  "derived": "A", "lineage": "D (ameríndio/asiático)"},
    {"pos": 10400, "derived": "T", "lineage": "M (macro asiático/ameríndio)"},
    {"pos": 10873, "derived": "C", "lineage": "L (macro africano)"},
    {"pos": 7028,  "derived": "C", "lineage": "H (europeu R0)"},
    {"pos": 12308, "derived": "G", "lineage": "U/K (europeu)"},
    {"pos": 13708, "derived": "A", "lineage": "J (europeu)"},
]

# --- (c) Alelos diagnósticos de ancestralidade -----------------------------
# rsid -> (gene, alelo/sinal populacional). Corroboram a ancestralidade
# maioritária; NÃO quantificam percentagens (isso exige análise genome-wide).
ANCESTRY_DIAGNOSTIC = {
    "rs16891982": ("SLC45A2", "Alelo G — forte sinal europeu (pele clara)"),
    "rs12913832": ("HERC2/OCA2", "Alelo G — olhos claros, enriquecido no N. da Europa"),
    "rs4988235":  ("MCM6/LCT", "Persistência da lactase — marca pastoralista indo-europeia"),
    "rs671":      ("ALDH2", "Alelo A quase exclusivo do Leste Asiático"),
    "rs3811801":  ("ADH1B", "Alelo do Leste Asiático (metabolismo do álcool)"),
    "rs2814778":  ("DARC/Duffy", "Alelo C (Duffy-null) — ancestralidade subsariana"),
    "rs12075":    ("DARC", "Antigénio Duffy Fya/Fyb (frequência varia por população)"),
    "rs1426654":  ("SLC24A5", "Alelo A — Europa/Médio Oriente/Sul da Ásia"),
    "rs3827760":  ("EDAR", "Alelo 370A — Leste Asiático/ameríndio"),
    "rs174570":   ("FADS", "Adaptação metabólica de dieta (varia por população)"),
}

# ==========================================================================
# SECÇÃO 6: PERFIL NEUROBIOLÓGICO (EXPLORATÓRIO — BAIXA EVIDÊNCIA)
# ==========================================================================
# Pontuação por eixos a partir de variantes candidatas, guiada por um mapa
# externo (neuro_map.json) editável. Os pesos são ILUSTRATIVOS: as
# associações gene→personalidade/cognição (COMT, BDNF, DRD2, HTR2A) têm
# efeitos pequenos e replicação fraca. NÃO é uma avaliação psicológica
# válida nem aconselhamento terapêutico — leitura recreativa/educativa.
NEURO_AXES = ("Execucao", "Resiliencia", "Plasticidade")

AXIS_DESCRIPTIONS = {
    "Execucao": "Controlo executivo, foco e regulação dopaminérgica (COMT, DRD2/3, DBH, atenção, ritmo).",
    "Resiliencia": "Regulação do stress e do humor (serotonina, oxitocina/opioide, endocanabinoides).",
    "Plasticidade": "Aprendizagem, memória e neuroplasticidade (BDNF, glutamato, metilação, manutenção APOE).",
}

# Contribuição do genótipo APOE composto para o eixo Plasticidade/manutenção.
# ε4 é fator de risco (Alzheimer/LDL) → penaliza; ε2 é protetor → bonifica.
APOE_NEURO_VALUE = {
    "ε2/ε2": 2, "ε2/ε3": 1, "ε3/ε3": 0, "ε2/ε4": 0, "ε3/ε4": -1, "ε4/ε4": -2,
}

# Mapa por omissão (esquema idêntico ao neuro_map.json).
DEFAULT_NEURO_MAP = {
    "rs4680": {
        "gene": "COMT",
        "pesos": {"GG": {"eixo": "Execucao", "valor": 2},
                  "AG": {"eixo": "Execucao", "valor": 0},
                  "AA": {"eixo": "Execucao", "valor": -2}},
        "estrategia": "Estrategia de Foco: se saldo negativo, prefira ambientes de alta estimulacao intelectual.",
    },
    "rs6265": {
        "gene": "BDNF",
        "pesos": {"GG": {"eixo": "Plasticidade", "valor": 2},
                  "AG": {"eixo": "Plasticidade", "valor": 0},
                  "AA": {"eixo": "Plasticidade", "valor": -2}},
        "estrategia": "Neuroplasticidade: praticar novos idiomas ou habilidades complexas acelera o desenvolvimento sinaptico.",
    },
}

_COMPLEMENT = {"A": "T", "T": "A", "C": "G", "G": "C"}


def load_neuro_map(path=None):
    """
    Carrega o mapa neuro de um ficheiro JSON. Se não for dado caminho,
    procura neuro_map.json na raiz do projeto; caindo no DEFAULT_NEURO_MAP.
    """
    import json
    import os
    candidate = path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "neuro_map.json")
    try:
        with open(candidate, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, ValueError):
        return DEFAULT_NEURO_MAP


def _match_weighted_genotype(genotype, weight_map):
    """
    Faz corresponder o genótipo às chaves do mapa de pesos, tolerando a
    ordem dos alelos E a cadeia (strand) — tenta o genótipo direto e o seu
    complemento. Devolve (chave_correspondente, invertido_por_strand) ou
    (None, False). Só se aplica a homozigotos definidos no mapa.
    """
    if not genotype or len(genotype) != 2:
        return None, False
    candidates = {genotype, genotype[::-1]}
    for c in list(candidates):
        if c in weight_map:
            return c, False
    # Tenta o complemento (ex.: CC no chip == GG na convenção do peso).
    comp = "".join(_COMPLEMENT.get(b, "?") for b in genotype)
    for c in {comp, comp[::-1]}:
        if c in weight_map:
            return c, True
    return None, False


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

    # -- Secção 5a: predição de pigmentação --------------------------------
    def predict_pigmentation(self):
        """Predição direcional de olhos/pele/cabelo (subconjunto HIrisPlex-S)."""
        covered = sum(1 for s in HIRISPLEX_PANEL
                      if self._genotype.get(s) not in (None, "--", ""))

        eye_g = self._genotype.get("rs12913832")
        skin_g = self._genotype.get("rs16891982")
        # Cabelo: MC1R (ruivo) + IRF4 (claro/escuro).
        mc1r = self._genotype.get("rs1805007")
        irf4 = self._genotype.get("rs12203592")
        if mc1r in ("CT", "TC", "TT"):
            hair = "Tendência para cabelo ruivo/claro (variante MC1R)"
        elif irf4 in ("TT", "CT", "TC"):
            hair = "Tendência para cabelo mais claro (loiro/castanho claro)"
        elif mc1r == "CC" and irf4 == "CC":
            hair = "Cabelo escuro provável (castanho/preto), sem variante ruiva"
        else:
            hair = "Indeterminado (marcadores insuficientes)"

        return {
            "coverage": covered, "panel_size": len(HIRISPLEX_PANEL),
            "eye": _lookup_genotype(eye_g, PIGMENT_EYE) if eye_g else "Indeterminado (rs12913832 ausente)",
            "eye_marker": f"rs12913832={eye_g}" if eye_g else "rs12913832 ausente",
            "skin": _lookup_genotype(skin_g, PIGMENT_SKIN) if skin_g else "Indeterminado (rs16891982 ausente)",
            "skin_marker": f"rs16891982={skin_g}" if skin_g else "rs16891982 ausente",
            "hair": hair,
        }

    # -- Secção 5b: rastreio da linhagem materna (mtDNA) -------------------
    def screen_maternal_lineage(self):
        """
        Rastreio EXCLUSIONÁRIO da linhagem materna a partir de posições
        mtDNA definidoras limpas. Não atribui haplogrupo — sinaliza que
        linhagens estão presentes/ausentes e remete para o mtHap.
        """
        mt = self.data[self.data["CHROMOSOME"].astype(str).str.upper() == "MT"]
        pos_to_base = {}
        for _, r in mt.iterrows():
            try:
                pos_to_base[int(r["POSITION"])] = str(r["RESULT"]).strip().upper()
            except (ValueError, TypeError):
                continue

        bases = {"A", "C", "G", "T"}
        checked, present_signals, absent_signals = [], [], []
        for m in MT_LINEAGE_MARKERS:
            base = pos_to_base.get(m["pos"])
            if base not in bases:  # ignora --, DD, II ou não coberto
                continue
            derived = base == m["derived"]
            entry = {"pos": m["pos"], "base": base, "derived": m["derived"],
                     "lineage": m["lineage"], "match": derived}
            checked.append(entry)
            (present_signals if derived else absent_signals).append(entry)

        # Conclusão conservadora, orientada por exclusão.
        amerind_asian = [e for e in checked if e["lineage"][0] in ("A", "C", "D", "M")]
        african = [e for e in checked if e["lineage"].startswith("L")]
        detected = [e for e in checked if e["match"]]

        if detected:
            linhas = ", ".join(sorted({e["lineage"] for e in detected}))
            conclusion = f"Sinal de linhagem detetado ({linhas}) — confirme no mtHap."
        elif amerind_asian:  # marcadores ameríndios/asiáticos limpos, todos ancestrais
            afr_note = ("" if african
                        else " (o marcador africano L não está coberto de forma limpa neste chip)")
            conclusion = ("Linhagens ameríndias (A/C/D) e do Leste Asiático (M) EXCLUÍDAS nas "
                          "posições limpas — padrão compatível com linhagem materna euroasiática "
                          "ocidental (europeia)." + afr_note)
        else:
            conclusion = "Cobertura insuficiente para uma conclusão — use o mtHap."

        return {
            "checked": checked, "present": present_signals, "absent": absent_signals,
            "conclusion": conclusion,
        }

    # -- Secção 5c: alelos diagnósticos de ancestralidade ------------------
    def analyze_ancestry_diagnostics(self):
        """Lista os alelos diagnósticos de ancestralidade presentes na amostra."""
        results = []
        for rsid, (gene, signal) in ANCESTRY_DIAGNOSTIC.items():
            genotype = self._genotype.get(rsid)
            present = genotype not in (None, "--", "")
            results.append({
                "rsid": rsid, "gene": gene, "signal": signal,
                "genotype": genotype if present else "—",
                "present": present,
            })
        return results

    # -- Secção 6: perfil neurobiológico (qualitativo) ---------------------
    def perfil_neuro(self, neuro_map=None):
        """
        Perfil neurobiológico QUALITATIVO (sem pontuação numérica), a partir
        do mapa (neuro_map.json). Para cada marcador determina um estado
        funcional — Favorável / Equilibrado / Sensível / Não coberto — e a
        função do sistema, organizando por eixo. APOE entra como genótipo
        composto (ε). EXPLORATÓRIO / baixa evidência.

        Devolve {'axes': {eixo: {markers, narrativa, contagem}}, 'strategies',
        'notes', 'sintese'}.
        """
        if neuro_map is None:
            neuro_map = load_neuro_map()

        by_axis = {a: [] for a in NEURO_AXES}
        strategies, notes = [], []

        def classify(value):
            return "Favorável" if value > 0 else "Sensível" if value < 0 else "Equilibrado"

        for rsid, info in neuro_map.items():
            if rsid == "rs7412":  # gerido pelo composto APOE
                continue
            pesos = info.get("pesos", {})
            # Eixo declarado no primeiro peso (todos os pesos de um marcador partilham eixo).
            axis = next(iter(pesos.values()), {}).get("eixo") if pesos else None
            genotype = self._genotype.get(rsid)
            entry = {"rsid": rsid, "gene": info.get("gene", "?"),
                     "sistema": info.get("sistema", ""), "funcao": info.get("funcao", ""),
                     "evidencia": info.get("evidencia", "?"), "ld_group": info.get("ld_group"),
                     "genotype": genotype or "—", "status": "Não coberto"}
            if genotype and genotype not in ("--", ""):
                key, flipped = _match_weighted_genotype(genotype, pesos)
                if key is None:
                    entry["status"] = "Equilibrado"
                else:
                    entry["status"] = classify(pesos[key]["valor"])
                    if flipped:
                        entry["genotype"] = f"{genotype} (=strand {key})"
                    if entry["status"] == "Sensível" and info.get("estrategia"):
                        strategies.append(info["estrategia"])
            if axis in by_axis:
                by_axis[axis].append(entry)

        # APOE composto -> Plasticidade / manutenção.
        apoe = resolve_apoe(self._genotype.get("rs429358"), self._genotype.get("rs7412"))
        if apoe:
            status = classify(APOE_NEURO_VALUE.get(apoe, 0))
            by_axis["Plasticidade"].append({
                "rsid": "APOE", "gene": f"APOE {apoe}", "sistema": "Manutenção lipídica/vascular",
                "funcao": "Metabolismo lipídico neuronal; risco de declínio cognitivo tardio",
                "evidencia": "alta", "ld_group": "APOE", "genotype": apoe, "status": status})
            if status == "Sensível":
                strategies.append("APOE: preservar integridade lipídica/vascular (dieta mediterrânica, "
                                  "exercício, sono, controlo de LDL) — relevante com ε4.")
            notes.append(f"APOE lido como genótipo composto {apoe} (rs429358+rs7412), coerente com a Secção 4.")

        # Narrativa por eixo.
        axes = {}
        for axis, markers in by_axis.items():
            cov = [m for m in markers if m["status"] != "Não coberto"]
            fav = [m for m in cov if m["status"] == "Favorável"]
            sen = [m for m in cov if m["status"] == "Sensível"]
            def genes(ms):
                return ", ".join(dict.fromkeys(m["gene"].split(" ")[0] for m in ms))
            if not cov:
                narr = "Sem marcadores cobertos neste eixo."
            elif sen:
                narr = (f"Predomínio equilibrado com áreas a apoiar em {genes(sen)}"
                        + (f"; pontos favoráveis em {genes(fav)}" if fav else "")
                        + ".")
            elif fav:
                narr = (f"Perfil equilibrado a favorável, com destaque positivo em "
                        f"{genes(fav)}; sem áreas sensíveis.")
            else:
                narr = "Perfil totalmente equilibrado (heterozigotos/neutros), sem picos nem défices."
            axes[axis] = {"markers": markers, "narrativa": narr,
                          "contagem": {"favoravel": len(fav), "sensivel": len(sen),
                                       "equilibrado": len(cov) - len(fav) - len(sen),
                                       "nao_coberto": len(markers) - len(cov)}}

        total_sen = sum(a["contagem"]["sensivel"] for a in axes.values())
        total_fav = sum(a["contagem"]["favoravel"] for a in axes.values())
        sintese = ("Perfil neurobiológico globalmente equilibrado. "
                   + (f"{total_fav} marcador(es) favorável(eis) e " if total_fav else "")
                   + (f"{total_sen} área(s) a apoiar." if total_sen
                      else "nenhuma área sensível assinalada."))
        return {"axes": axes, "strategies": list(dict.fromkeys(strategies)),
                "notes": notes, "sintese": sintese}

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

        pig = self.predict_pigmentation()
        lineage = self.screen_maternal_lineage()
        diag = self.analyze_ancestry_diagnostics()
        add("[5] ANCESTRALIDADE & FENÓTIPO GLOBAL")
        add(f"  -- (a) Pigmentação predita [cobertura {pig['coverage']}/{pig['panel_size']} "
            f"do painel HIrisPlex-S] --")
        add(f"    Olhos: {pig['eye']}  ({pig['eye_marker']})")
        add(f"    Pele:  {pig['skin']}  ({pig['skin_marker']})")
        add(f"    Cabelo: {pig['hair']}")
        add("    ⚠ Predição direcional (cobertura parcial), não a probabilidade forense validada.")
        add("")
        add("  -- (b) Linhagem materna (mtDNA, rastreio exclusionário) --")
        for e in lineage["checked"]:
            flag = "presente" if e["match"] else "ausente"
            add(f"    Pos {e['pos']}: base {e['base']} → sinal {e['lineage']}: {flag}")
        add(f"    ↳ {lineage['conclusion']}")
        add("    ⚠ Haplogrupo definitivo requer o mtHap (ficheiro exportado).")
        add("")
        add("  -- (c) Alelos diagnósticos de ancestralidade --")
        for d in diag:
            if d["present"]:
                add(f"    [{d['rsid']}] {d['gene']} | Genótipo: {d['genotype']} → {d['signal']}")
            else:
                add(f"    [{d['rsid']}] {d['gene']} | ausente do chip ({d['signal']})")
        add("    ⚠ Corroboram a ancestralidade maioritária; NÃO quantificam percentagens")
        add("      (componentes minoritários de ~3-4% exigem análise genome-wide com painéis).")
        add("")

        neuro = self.perfil_neuro()
        add("[6] PERFIL NEUROBIOLÓGICO (QUALITATIVO — EXPLORATÓRIO, BAIXA EVIDÊNCIA)")
        add(f"    Síntese: {neuro['sintese']}")
        for n in neuro["notes"]:
            add(f"    Nota: {n}")
        add("")
        for axis in NEURO_AXES:
            a = neuro["axes"][axis]
            c = a["contagem"]
            add(f"  == {axis.upper()} ==  ({AXIS_DESCRIPTIONS[axis]})")
            add(f"     Leitura: {a['narrativa']}")
            add(f"     (favoráveis: {c['favoravel']} | equilibrados: {c['equilibrado']} "
                f"| sensíveis: {c['sensivel']} | não cobertos: {c['nao_coberto']})")
            for e in a["markers"]:
                ld = f" [LD:{e['ld_group']}]" if e.get("ld_group") else ""
                add(f"       • {e['gene']}{ld} [{e['sistema']}] — Genótipo {e['genotype']} "
                    f"→ {e['status']} (evid: {e['evidencia']})")
                add(f"         Função: {e['funcao']}")
            add("")
        add("  -- Áreas a apoiar (estratégias exploratórias, não terapêuticas) --")
        if neuro["strategies"]:
            for s in neuro["strategies"]:
                add(f"      - {s}")
        else:
            add("      Nenhuma área sensível sinalizada — perfil equilibrado nos eixos avaliados.")
        add("    ⚠ Leitura ILUSTRATIVA por sistema de neurotransmissores. As associações")
        add("      gene→comportamento têm efeito pequeno e replicação fraca. NÃO é avaliação psicológica.")
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

        # -- Secção 5 --
        pig = self.predict_pigmentation()
        lineage = self.screen_maternal_lineage()
        diag = self.analyze_ancestry_diagnostics()
        add("## 5. Ancestralidade & fenótipo global")
        add("")
        add(f"### (a) Pigmentação predita — cobertura {pig['coverage']}/{pig['panel_size']} "
            f"do painel HIrisPlex-S")
        add("")
        add("| Traço | Predição | Marcador |")
        add("|-------|----------|----------|")
        add(f"| Olhos | {pig['eye']} | `{pig['eye_marker']}` |")
        add(f"| Pele | {pig['skin']} | `{pig['skin_marker']}` |")
        add(f"| Cabelo | {pig['hair']} | rs1805007 / rs12203592 |")
        add("")
        add("> ⚠️ Predição **direcional** (cobertura parcial), não a probabilidade forense validada.")
        add("")
        add("### (b) Linhagem materna (mtDNA — rastreio exclusionário)")
        add("")
        add("| Posição rCRS | Base no chip | Sinal de linhagem | Estado |")
        add("|:------------:|:------------:|-------------------|:------:|")
        for e in lineage["checked"]:
            add(f"| {e['pos']} | `{e['base']}` | {e['lineage']} | "
                f"{'presente' if e['match'] else 'ausente'} |")
        add("")
        add(f"**Conclusão:** {lineage['conclusion']}")
        add("")
        add("> ⚠️ O haplogrupo **definitivo** requer o mtHap (o ficheiro `mtdna_mthap.txt` já exportado).")
        add("")
        add("### (c) Alelos diagnósticos de ancestralidade")
        add("")
        add("| RSID | Gene | Genótipo | Sinal populacional |")
        add("|------|------|:--------:|--------------------|")
        for d in diag:
            geno = f"`{d['genotype']}`" if d["present"] else "_ausente_"
            add(f"| `{d['rsid']}` | {d['gene']} | {geno} | {d['signal']} |")
        add("")
        add("> ⚠️ Corroboram a ancestralidade **maioritária**; **não** quantificam percentagens — "
            "componentes minoritários (~3-4%) exigem análise genome-wide com painéis de referência "
            "(1000 Genomes/HGDP) e ferramentas como ADMIXTURE/RFMix.")
        add("")

        # -- Secção 6 --
        neuro = self.perfil_neuro()
        add("## 6. Perfil neurobiológico (qualitativo — exploratório, baixa evidência)")
        add("")
        add(f"**Síntese:** {neuro['sintese']}")
        add("")
        for n in neuro["notes"]:
            add(f"> ℹ️ {n}")
        if neuro["notes"]:
            add("")
        for axis in NEURO_AXES:
            a = neuro["axes"][axis]
            add(f"### {axis} — {AXIS_DESCRIPTIONS[axis]}")
            add("")
            add(f"_{a['narrativa']}_")
            add("")
            add("| Gene | Sistema | Genótipo | Estado | Evid. | Função |")
            add("|------|---------|:--------:|:------:|:-----:|--------|")
            for e in a["markers"]:
                gene = e["gene"] + (f" · LD:{e['ld_group']}" if e.get("ld_group") else "")
                add(f"| {gene} | {e['sistema']} | `{e['genotype']}` | **{e['status']}** "
                    f"| {e['evidencia']} | {e['funcao']} |")
            add("")
        add("**Áreas a apoiar** (estratégias exploratórias, não terapêuticas):")
        add("")
        if neuro["strategies"]:
            for s in neuro["strategies"]:
                add(f"- {s}")
        else:
            add("- _Nenhuma área sensível sinalizada — perfil equilibrado nos eixos avaliados._")
        add("")
        add("> ⚠️ Leitura **ilustrativa** por sistema de neurotransmissores; APOE como genótipo composto (ε). "
            "As associações gene→comportamento têm efeito pequeno e replicação fraca — **não** é uma "
            "avaliação psicológica válida nem aconselhamento terapêutico.")
        add("")

        add("---")
        add("")
        add("> **Aviso:** Relatório de **rastreio** sobre dados de genotipagem por chip "
            "(cobertura parcial do genoma). As interpretações são indicativas e **não "
            "diagnósticas** — a ausência de uma variante não garante a sua ausência no "
            "genoma. Não tome decisões médicas com base neste relatório; para qualquer "
            "achado relevante procure confirmação clínica e aconselhamento genético.")

        return "\n".join(lines)
