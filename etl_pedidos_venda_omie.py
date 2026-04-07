import psycopg2
import pandas as pd
import requests as r
import logging
import json
import numpy as np
from datetime import datetime, timedelta, date
import time
from dotenv import load_dotenv
import os

'''
default_args = {
    'owner': 'caio.cesar',
    'depends_on_past': False,
    'email': ['caio.cesar.dec15@gmail'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(minutes=1),
}
'''

# Definindo a data inicial e final da extração
# A api do OMIE utiliza a data de atualização do registro como parametro
from_date = (datetime.today() - timedelta(days=7)).strftime('%d-%m-%Y')
# from_date = '01-01-2022'
to_date = datetime.today().strftime('%d-%m-%Y')
# to_date = '31-12-2022'

# Lista de credenciais
credentials_list = [
    {
        "app_name": "Filial 1",
        "app_key": "xxxxxxxxxxxxx",
        "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    },
    {
        "app_name": "Filial 2",
        "app_key": "xxxxxxxxxxxxx",
        "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    }
]

# Configuração do banco de dados
# db_conn_id = 'plat_vendas'
db_config = {
    "dbname": "dbname",
    "user": "user",
    "password": "password",
    "host": "0.0.0.0",
    "port": "0000"
}

list_pedidos_omie = []
list_produtos_omie = []
resultados_status = []
# ti = kwargs['ti']

url_pedido_omie = 'https://app.omie.com.br/api/v1/produtos/pedido/'
headers = {
    'Content-Type': 'application/json'
}

for cred in credentials_list:

    payload = {
        "call": "ListarPedidos",
        "app_name": cred["app_name"],
        "app_key": cred["app_key"],
        "app_secret": cred["app_secret"],
        "param": [{
            "pagina": 1,
            "registros_por_pagina": 50,
            "apenas_importado_api": "N",
            "filtrar_por_data_de": from_date,
            "filtrar_por_data_ate": to_date
        }]
    }

    try:
        response = r.post(url_pedido_omie, json=payload, timeout=120)
        data = response.json()
        
        pagina = data.get("pagina", 1)
        total_paginas = data.get("total_de_paginas", 1)
        total_registros = data.get("total_de_registros", 1)
        # total_paginas = 2
        nome_app = cred["app_name"]

        # Iniciando o loop de paginas
        while pagina <= total_paginas:
            
            payload["param"][0]["pagina"] = pagina
            response = r.post(url_pedido_omie, json=payload, timeout=120)
            data = response.json()

            print(f"Extraindo pag {pagina} de {total_paginas} dp app {nome_app}")

            pedidos = data.get("pedido_venda_produto", [])

            # Iniciando os pedidos da página
            for pedido in pedidos:

                cabecalho = pedido.get("cabecalho", {})
                totais = pedido.get("total_pedido", {})
                infoCadastro = pedido.get("infoCadastro", {})
                infoAdicionais = pedido.get("informacoes_adicionais", {})
                outrosDetalhes = infoAdicionais.get("outros_detalhes", {})

                cod_pedido = cabecalho.get("codigo_pedido")
                print(f"Coletando dados do pedido: {cod_pedido}")

                # Vai ser usado pros detalhes da NF
                payload2 = {
                    "call": "StatusPedido",
                    "app_name": cred["app_name"],
                    "app_key": cred["app_key"],
                    "app_secret": cred["app_secret"],
                    "param": [{
                        "codigo_pedido": cod_pedido
                    }]
                }

                # Convertendo as datas pro formato do banco
                data_previsao = datetime.strptime(cabecalho["data_previsao"], "%d/%m/%Y").strftime("%Y-%m-%d") if cabecalho.get("data_previsao") else None
                dInc = datetime.strptime(infoCadastro["dInc"], "%d/%m/%Y").strftime("%Y-%m-%d") if infoCadastro.get("dInc") else None
                dFat = datetime.strptime(infoCadastro["dFat"], "%d/%m/%Y").strftime("%Y-%m-%d") if infoCadastro.get("dFat") else None
                dAlt = datetime.strptime(infoCadastro["dAlt"], "%d/%m/%Y").strftime("%Y-%m-%d") if infoCadastro.get("dAlt") else None

                # Lista de Pedidos
                list_pedidos_omie.append({
                    # Geral Pedido
                    "nome_app": nome_app,
                    "codigo_empresa": cabecalho.get("codigo_empresa"),
                    "codigo_pedido": cabecalho.get("codigo_pedido"),
                    "codigo_pedido_integracao": cabecalho.get("codigo_pedido_integracao"),
                    "numero_pedido": cabecalho.get("numero_pedido"),
                    "codigo_cliente": cabecalho.get("codigo_cliente"),
                    "etapa": cabecalho.get("etapa"),
                    "importado_api": cabecalho.get("importado_api"),
                    "origem_pedido": cabecalho.get("origem_pedido"),
                    "codigo_parcela": cabecalho.get("codigo_parcela"),
                    "qtde_parcelas": cabecalho.get("qtde_parcelas"),
                    "quantidade_itens": cabecalho.get("quantidade_itens"),
                    "data_previsao": data_previsao,
                    #InfoCadastro
                    "autorizado": infoCadastro.get("autorizado"),
                    "cancelado": infoCadastro.get("cancelado"),
                    "denegado": infoCadastro.get("denegado"),
                    "devolvido": infoCadastro.get("devolvido"),
                    "devolvido_parcial": infoCadastro.get("devolvido_parcial"),
                    "faturado": infoCadastro.get("faturado"),
                    "dInc": dInc,
                    "dFat": dFat,
                    "dAlt": dAlt,
                    "hInc": infoCadastro.get("hInc"),
                    "hFat": infoCadastro.get("hFat"),
                    "hAlt": infoCadastro.get("hAlt"),
                    "uInc": infoCadastro.get("uInc"),
                    "uFat": infoCadastro.get("uFat"),
                    "uAlt": infoCadastro.get("uAlt"),
                    # Informações Adicionais
                    "codVend": infoAdicionais.get("codVend"),
                    "codigo_categoria": infoAdicionais.get("codigo_categoria"),
                    "codigo_conta_corrente": infoAdicionais.get("codigo_conta_corrente"),
                    "consumidor_final": infoAdicionais.get("consumidor_final"),
                    "contato": infoAdicionais.get("contato"),
                    "utilizar_emails": infoAdicionais.get("utilizar_emails"),
                    "dados_adicionais_nf": (infoAdicionais.get("dados_adicionais_nf")[:240] if infoAdicionais.get("dados_adicionais_nf") else None),
                    "enviar_email": infoAdicionais.get("enviar_email"),
                    "enviar_pix": infoAdicionais.get("enviar_pix"),
                    "numero_contrato": infoAdicionais.get("numero_contrato"),
                    "numero_pedido_cliente": infoAdicionais.get("numero_pedido_cliente"),
                    # Outros detalhes
                    "cBairroOd": outrosDetalhes.get("cBairroOd"),
                    "cCEPOd": outrosDetalhes.get("cCEPOd"),
                    "cCidadeOd": outrosDetalhes.get("cCidadeOd"),
                    "cCnpjCpfOd": outrosDetalhes.get("cCnpjCpfOd"),
                    "cComplementoOd": outrosDetalhes.get("cComplementoOd"),
                    "cEnderecoOd": outrosDetalhes.get("cEnderecoOd"),
                    "cEstadoOd": outrosDetalhes.get("cEstadoOd"),
                    "cNomeOd": outrosDetalhes.get("cNomeOd"),
                    "cNumeroOd": outrosDetalhes.get("cNumeroOd"),
                    # Totais
                    "base_calculo_icms": totais.get("base_calculo_icms"),
                    "base_calculo_st": totais.get("base_calculo_st"),
                    "valor_IPI": totais.get("valor_IPI"),
                    "valor_cofins": totais.get("valor_cofins"),
                    "valor_csll": totais.get("valor_csll"),
                    "valor_deducoes": totais.get("valor_deducoes"),
                    "valor_descontos": totais.get("valor_descontos"),
                    "valor_icms": totais.get("valor_icms"),
                    "valor_inss": totais.get("valor_inss"),
                    "valor_ir": totais.get("valor_ir"),
                    "valor_iss": totais.get("valor_iss"),
                    "valor_mercadorias": totais.get("valor_mercadorias"),
                    "valor_pis": totais.get("valor_pis"),
                    "valor_st": totais.get("valor_st"),
                    "valor_total_pedido": totais.get("valor_total_pedido")
                })
                
                # Coleta de itens dos pedidos
                for item in pedido.get("det", []):
                    produto = item.get("produto", {})

                    cod_produto = produto.get("codigo_produto")

                    list_produtos_omie.append({
                        "id": str(cod_pedido) + "-" + str(cod_produto),
                        "nome_app": nome_app,
                        "codigo_empresa": cabecalho.get("codigo_empresa"),
                        "codigo_pedido": cabecalho.get("codigo_pedido"),
                        "codigo_pedido_integracao": cabecalho.get("codigo_pedido_integracao"),
                        "cfop": produto.get("cfop"),
                        "cnpj_fabricante": produto.get("cnpj_fabricante"),
                        "codigo": produto.get("codigo"),
                        "codigo_produto": produto.get("codigo_produto"),
                        "codigo_tabela_preco": produto.get("codigo_tabela_preco"),
                        "descricao": produto.get("descricao"),
                        "ean": produto.get("ean"),
                        "indicador_escala": produto.get("indicador_escala"),
                        "kit": produto.get("kit"),
                        "motivo_icms_desonerado": produto.get("motivo_icms_desonerado"),
                        "ncm": produto.get("ncm"),
                        "percentual_desconto": produto.get("percentual_desconto"),
                        "quantidade": produto.get("quantidade"),
                        "reservado": produto.get("cforeservadop"),
                        "tipo_desconto": produto.get("tipo_desconto"),
                        "unidade": produto.get("unidade"),
                        "valor_deducao": produto.get("valor_deducao"),
                        "valor_desconto": produto.get("valor_desconto"),
                        "valor_icms_desonerado": produto.get("valor_icms_desonerado"),
                        "valor_mercadoria": produto.get("valor_mercadoria"),
                        "valor_total": produto.get("valor_total"),
                        "valor_unitario": produto.get("valor_unitario")
                    })

                # Iniciando coleta de detalhes da NF
                max_retries = 10
                for attempt in range(1, max_retries + 1):
                    try:
                        resp = r.post(url_pedido_omie, json=payload2, timeout=120)
                        resp.raise_for_status()
                        dados = resp.json()

                        lista_nfe = dados.get("ListaNfe", []) if isinstance(dados.get("ListaNfe", []), list) else []
                        for nfe in lista_nfe:
                            resultados_status.append({
                                "codigo_pedido": dados.get("codigo_pedido"),
                                "ambiente": dados.get("ambiente"),
                                "chave_nfe": nfe.get("chave_nfe"),
                                "contingencia": nfe.get("contingencia"),
                                "numero_lote": nfe.get("numero_lote"),
                                "numero_nfe": nfe.get("numero_nfe"),
                                "protocolo": nfe.get("protocolo"),
                                "recibo": nfe.get("recibo"),
                                "serie_nfe": nfe.get("serie_nfe"),
                                "status_lote": nfe.get("status_lote"),
                                "status_nfe": nfe.get("status_nfe"),
                                "tipo": nfe.get("tipo")
                            })
                        break  # Sai do loop se deu certo

                    except Exception as e:
                        print(f"Tentativa {attempt}/{max_retries} falhou ao buscar status do pedido {cod_pedido}: {e}")
                        if attempt == max_retries:
                            print(f"Falhou definitivamente para o pedido {cod_pedido}")
                        else:
                            time.sleep(5)  # timer entre as tentativas
        
            pagina = pagina +1
            time.sleep(5)

    except Exception as e:
        print(f"Erro ao processar app {cred['app_name']}: {e}") 

df_pedidos = pd.DataFrame(list_pedidos_omie)
df_itens_to_insert = pd.DataFrame(list_produtos_omie)
df_detalhes_nf = pd.DataFrame(resultados_status)

# Mesclando os 2 dataframes
df_to_insert = pd.merge(
    df_pedidos,
    df_detalhes_nf,
    on="codigo_pedido",
    how="left" # tipo do join
)

# Remove duplicatas por segurança
df_to_insert = df_to_insert.drop_duplicates(subset=['codigo_pedido'])
# Substituir "None" e "nan" por NULL
df_to_insert.replace({np.nan: None, 'None': None, '': None, 'nan': None, 'NaN': None, 'NaT': None}, inplace=True)

# df_to_insert.to_excel("pedidos.xlsx", index=False)
# df_itens_to_insert.to_excel("itens.xlsx", index=False)

num_pedidos_coletados = len(df_to_insert)
num_itens_pedido_coletados = len(df_itens_to_insert)

print(f"Pedidos Coletados: {num_pedidos_coletados}")
print(f"Itens Coletados: {num_itens_pedido_coletados}")


query_pedidos = """
INSERT INTO schema.tbl_pedidos (
    nome_app, codigo_empresa, codigo_pedido, codigo_pedido_integracao,
    numero_pedido, numero_nfe, codigo_cliente, etapa,importado_api, origem_pedido, codigo_parcela,
    qtde_parcelas, quantidade_itens, data_previsao, autorizado, cancelado, denegado, devolvido, devolvido_parcial,
    faturado, dInc, dFat, dAlt, hInc, hFat, hAlt, uInc, uFat, uAlt, codVend, codigo_categoria, codigo_conta_corrente,
    consumidor_final, contato, utilizar_emails, dados_adicionais_nf, enviar_email, enviar_pix, numero_contrato, 
    numero_pedido_cliente, cBairroOd, cCEPOd, cCidadeOd, cCnpjCpfOd, cComplementoOd, cEnderecoOd, cEstadoOd, cNomeOd,
    cNumeroOd, base_calculo_icms, base_calculo_st, valor_IPI, valor_cofins, valor_csll, valor_deducoes, valor_descontos,
    valor_icms, valor_inss, valor_ir, valor_iss, valor_mercadorias, valor_pis, valor_st, valor_total_pedido, ambiente,
    chave_nfe, contingencia, numero_lote, protocolo, recibo, serie_nfe, status_lote, status_nfe, tipo
)
VALUES (
    %(nome_app)s, %(codigo_empresa)s, %(codigo_pedido)s, %(codigo_pedido_integracao)s, %(numero_pedido)s, %(numero_nfe)s,
    %(codigo_cliente)s, %(etapa)s, %(importado_api)s, %(origem_pedido)s, %(codigo_parcela)s, %(qtde_parcelas)s,
    %(quantidade_itens)s, %(data_previsao)s, %(autorizado)s, %(cancelado)s, %(denegado)s, %(devolvido)s,
    %(devolvido_parcial)s, %(faturado)s, %(dInc)s, %(dFat)s, %(dAlt)s, %(hInc)s, %(hFat)s, %(hAlt)s, %(uInc)s,
    %(uFat)s, %(uAlt)s, %(codVend)s, %(codigo_categoria)s, %(codigo_conta_corrente)s, %(consumidor_final)s,
    %(contato)s, %(utilizar_emails)s, %(dados_adicionais_nf)s, %(enviar_email)s, %(enviar_pix)s, %(numero_contrato)s,
    %(numero_pedido_cliente)s, %(cBairroOd)s, %(cCEPOd)s, %(cCidadeOd)s, %(cCnpjCpfOd)s, %(cComplementoOd)s,
    %(cEnderecoOd)s, %(cEstadoOd)s,%(cNomeOd)s,%(cNumeroOd)s,%(base_calculo_icms)s, %(base_calculo_st)s,
    %(valor_IPI)s, %(valor_cofins)s,%(valor_csll)s,%(valor_deducoes)s,%(valor_descontos)s,%(valor_icms)s,
    %(valor_inss)s, %(valor_ir)s, %(valor_iss)s, %(valor_mercadorias)s, %(valor_pis)s, %(valor_st)s,
    %(valor_total_pedido)s, %(ambiente)s, %(chave_nfe)s, %(contingencia)s, %(numero_lote)s, %(protocolo)s, %(recibo)s,
    %(serie_nfe)s, %(status_lote)s, %(status_nfe)s, %(tipo)s
)
ON CONFLICT (codigo_pedido) DO UPDATE SET
    nome_app = EXCLUDED.nome_app,
    codigo_empresa = EXCLUDED.codigo_empresa,
    codigo_pedido_integracao = EXCLUDED.codigo_pedido_integracao,
    numero_pedido = EXCLUDED.numero_pedido,
    numero_nfe = EXCLUDED.numero_nfe,
    codigo_cliente = EXCLUDED.codigo_cliente,
    etapa = EXCLUDED.etapa,
    importado_api = EXCLUDED.importado_api,
    origem_pedido = EXCLUDED.origem_pedido,
    codigo_parcela = EXCLUDED.codigo_parcela,
    qtde_parcelas = EXCLUDED.qtde_parcelas,
    quantidade_itens = EXCLUDED.quantidade_itens,
    data_previsao = EXCLUDED.data_previsao,
    autorizado = EXCLUDED.autorizado,
    cancelado = EXCLUDED.cancelado,
    denegado = EXCLUDED.denegado,
    devolvido = EXCLUDED.devolvido,
    devolvido_parcial = EXCLUDED.devolvido_parcial,
    faturado = EXCLUDED.faturado,
    dInc = EXCLUDED.dInc,
    dFat = EXCLUDED.dFat,
    dAlt = EXCLUDED.dAlt,
    hInc = EXCLUDED.hInc,
    hFat = EXCLUDED.hFat,
    hAlt = EXCLUDED.hAlt,
    uInc = EXCLUDED.uInc,
    uFat = EXCLUDED.uFat,
    uAlt = EXCLUDED.uAlt,
    codVend = EXCLUDED.codVend,
    codigo_categoria = EXCLUDED.codigo_categoria,
    codigo_conta_corrente = EXCLUDED.codigo_conta_corrente,
    consumidor_final = EXCLUDED.consumidor_final,
    contato = EXCLUDED.contato,
    utilizar_emails = EXCLUDED.utilizar_emails,
    dados_adicionais_nf = EXCLUDED.dados_adicionais_nf,
    enviar_email = EXCLUDED.enviar_email,
    enviar_pix = EXCLUDED.enviar_pix,
    numero_contrato = EXCLUDED.numero_contrato,
    numero_pedido_cliente = EXCLUDED.numero_pedido_cliente,
    cBairroOd = EXCLUDED.cBairroOd,
    cCEPOd = EXCLUDED.cCEPOd,
    cCidadeOd = EXCLUDED.cCidadeOd,
    cCnpjCpfOd = EXCLUDED.cCnpjCpfOd,
    cComplementoOd = EXCLUDED.cComplementoOd,
    cEnderecoOd = EXCLUDED.cEnderecoOd,
    cEstadoOd = EXCLUDED.cEstadoOd,
    cNomeOd = EXCLUDED.cNomeOd,
    cNumeroOd = EXCLUDED.cNumeroOd,
    base_calculo_icms = EXCLUDED.base_calculo_icms,
    base_calculo_st = EXCLUDED.base_calculo_st,
    valor_IPI = EXCLUDED.valor_IPI,
    valor_cofins = EXCLUDED.valor_cofins,
    valor_csll = EXCLUDED.valor_csll,
    valor_deducoes = EXCLUDED.valor_deducoes,
    valor_descontos = EXCLUDED.valor_descontos,
    valor_icms = EXCLUDED.valor_icms,
    valor_inss = EXCLUDED.valor_inss,
    valor_ir = EXCLUDED.valor_ir,
    valor_iss = EXCLUDED.valor_iss,
    valor_mercadorias = EXCLUDED.valor_mercadorias,
    valor_pis = EXCLUDED.valor_pis,
    valor_st = EXCLUDED.valor_st,
    valor_total_pedido = EXCLUDED.valor_total_pedido,
    ambiente = EXCLUDED.ambiente,
    chave_nfe = EXCLUDED.chave_nfe,
    contingencia = EXCLUDED.contingencia,
    numero_lote = EXCLUDED.numero_lote,
    protocolo = EXCLUDED.protocolo,
    recibo = EXCLUDED.recibo,
    serie_nfe = EXCLUDED.serie_nfe,
    status_lote = EXCLUDED.status_lote,
    status_nfe = EXCLUDED.status_nfe,
    tipo = EXCLUDED.tipo;
"""

query_itens = """
INSERT INTO schema.tbl_itens_pedidos (
    id, nome_app, codigo_empresa, codigo_pedido, codigo_pedido_integracao, cfop, cnpj_fabricante, codigo,
    codigo_produto, codigo_tabela_preco, descricao, ean, indicador_escala, kit, motivo_icms_desonerado,
    ncm, percentual_desconto, quantidade, reservado, tipo_desconto, unidade,valor_deducao,valor_desconto,
    valor_icms_desonerado,valor_mercadoria,valor_total,valor_unitario
)
VALUES (
    %(id)s, %(nome_app)s, %(codigo_empresa)s, %(codigo_pedido)s, %(codigo_pedido_integracao)s, %(cfop)s,
    %(cnpj_fabricante)s, %(codigo)s, %(codigo_produto)s, %(codigo_tabela_preco)s, %(descricao)s, %(ean)s,
    %(indicador_escala)s, %(kit)s, %(motivo_icms_desonerado)s, %(ncm)s, %(percentual_desconto)s, %(quantidade)s,
    %(reservado)s, %(tipo_desconto)s, %(unidade)s, %(valor_deducao)s, %(valor_desconto)s, %(valor_icms_desonerado)s,
    %(valor_mercadoria)s, %(valor_total)s, %(valor_unitario)s
)
ON CONFLICT (id) DO UPDATE SET
    nome_app = EXCLUDED.nome_app,
    codigo_empresa = EXCLUDED.codigo_empresa,
    codigo_pedido = EXCLUDED.codigo_pedido,
    codigo_pedido_integracao = EXCLUDED.codigo_pedido_integracao,
    cfop = EXCLUDED.cfop,
    cnpj_fabricante = EXCLUDED.cnpj_fabricante,
    codigo = EXCLUDED.codigo,
    codigo_produto = EXCLUDED.codigo_produto,
    codigo_tabela_preco = EXCLUDED.codigo_tabela_preco,
    descricao = EXCLUDED.descricao,
    ean = EXCLUDED.ean,
    indicador_escala = EXCLUDED.indicador_escala,
    kit = EXCLUDED.kit,
    motivo_icms_desonerado = EXCLUDED.motivo_icms_desonerado,
    ncm = EXCLUDED.ncm,
    percentual_desconto = EXCLUDED.percentual_desconto,
    quantidade = EXCLUDED.quantidade,
    reservado = EXCLUDED.reservado,
    tipo_desconto = EXCLUDED.tipo_desconto,
    unidade = EXCLUDED.unidade,
    valor_deducao = EXCLUDED.valor_deducao,
    valor_desconto = EXCLUDED.valor_desconto,
    valor_icms_desonerado = EXCLUDED.valor_icms_desonerado,
    valor_mercadoria = EXCLUDED.valor_mercadoria,
    valor_total = EXCLUDED.valor_total,
    valor_unitario = EXCLUDED.valor_unitario;
"""

conn = psycopg2.connect(**db_config)
cur = conn.cursor()
print("Conectado ao banco de dados!")

print("Inserindo Pedidos!")
for _, row in df_to_insert.iterrows():
    try:
        data = {key: value for key, value in row.items()}
        cur.execute(query_pedidos, data)
    except Exception as e:
        print(f"Erro ao inserir o registro (pedido: {cod_pedido}): {e}")
        print(f"Registro com erro: {row.to_dict()}")
conn.commit()
print("Inserindo Itens!")

for _, row in df_itens_to_insert.iterrows():
    try:
        data = {key: value for key, value in row.items()}
        cur.execute(query_itens, data)
    except Exception as e:
        print(f"Erro ao inserir o itens (pedido: {cod_pedido}): {e}")
        print(f"Registro com erro: {row.to_dict()}")
conn.commit()

cur.close()
conn.close()
print("Conexão encerrada com sucesso!")
