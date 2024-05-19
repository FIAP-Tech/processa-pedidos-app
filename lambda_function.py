import json
import boto3
import datetime
import http.client

sqs = boto3.client('sqs')
queue_url_processa_entregas = 'https://sqs.us-east-1.amazonaws.com/672291737467/processa-entregas'
queue_url_envia_emails = 'https://sqs.us-east-1.amazonaws.com/672291737467/envia-emails'

def lambda_handler(event, context):
    sqs_message = json.loads(event['Records'][0]['body'])

    pedido_id = sqs_message.get('idPedido')
    pedido_produtos = sqs_message.get('pedidoProdutos')
    total_pedido = sqs_message.get('totalPedido')
    forma_pagamento = sqs_message.get('formaPagamento')
    nome_cliente = sqs_message.get('cliente', {}).get('nome')

    envia_para_fila_processa_pedidos = False
    status_pedido = "PAGAMENTO_EFETUADO"

    if forma_pagamento == 'BOLETO':
        envia_para_fila_processa_pedidos = True

    elif forma_pagamento == 'CARTAO_CREDITO':
        validade = sqs_message.get('validadeFormaPagamentoCartao')
        if validade:
            mes_validade, ano_validade = map(int, validade.split('/'))
            data_validade = datetime.date(ano_validade, mes_validade, 1)
            data_hoje = datetime.date.today()

            if data_validade >= data_hoje:
                envia_para_fila_processa_pedidos = True
            else:
                envia_para_fila_processa_pedidos = False
                status_pedido = "FALHA_NO_PAGAMENTO"

    if envia_para_fila_processa_pedidos:
        sqs.send_message(
            QueueUrl=queue_url_processa_entregas,
            MessageBody=json.dumps(sqs_message)
        )

    url = f"https://pedidos-app-step4-4a5a9f7b65f6.herokuapp.com/api/pedidos/{pedido_id}/status?status={status_pedido}"
    conn = http.client.HTTPSConnection("pedidos-app-step4-4a5a9f7b65f6.herokuapp.com")
    conn.request("PATCH", url)
    response = conn.getresponse()
    conn.close()

    assunto_email, corpo_email = create_email_body(nome_cliente, pedido_produtos, total_pedido, envia_para_fila_processa_pedidos)

    email_payload = {
        "emailDestinatario": sqs_message.get('cliente', {}).get('email'),
        "assunto": assunto_email,
        "corpoEmail": corpo_email
    }

    sqs.send_message(
        QueueUrl=queue_url_envia_emails,
        MessageBody=json.dumps(email_payload)
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Processamento de pedidos concluído com sucesso!')
    }


def create_email_body(nome_cliente, pedido_produtos, total_pedido, pagamento_com_sucesso):
    assunto_email = "Pagamento do pedido foi efetuado com sucesso" if pagamento_com_sucesso else "Falha ao processar o pagamento do pedido"

    # Construindo a parte HTML para os produtos do pedido
    produtos_html = ""
    for produto in pedido_produtos:
        produtos_html += "<tr>\n" + \
                         f"    <td>{produto['descricao']}</td>\n" + \
                         f"    <td>R$ {produto['preco']:,.2f}</td>\n" + \
                         f"    <td>{produto['quantidade']}</td>\n" + \
                         f"    <td>R$ {produto['preco'] * produto['quantidade']:,.2f}</td>\n" + \
                         "</tr>\n"

    corpo_email = f"<!DOCTYPE html>\n" + \
                  "<html lang=\"pt-BR\">\n" + \
                  "<head>\n" + \
                  "    <meta charset=\"UTF-8\">\n" + \
                  "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" + \
                  "    <title>{}</title>\n".format(assunto_email) + \
                  "    <style>\n" + \
                  "        body {\n" + \
                  "            font-family: 'Arial', sans-serif;\n" + \
                  "            background-color: #F8F8F8;\n" + \
                  "            color: #333;\n" + \
                  "            margin: 0;\n" + \
                  "            padding: 0;\n" + \
                  "        }\n" + \
                  "        .container {\n" + \
                  "            max-width: 600px;\n" + \
                  "            margin: 0 auto;\n" + \
                  "            padding: 20px;\n" + \
                  "            background-color: #FFFFFF;\n" + \
                  "            border-radius: 8px;\n" + \
                  "            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);\n" + \
                  "        }\n" + \
                  "        h1, h2, p {\n" + \
                  "            margin-top: 0;\n" + \
                  "            margin-bottom: 20px;\n" + \
                  "        }\n" + \
                  "        h1 {\n" + \
                  "            color: #00215E;\n" + \
                  "            font-size: 24px;\n" + \
                  "            font-weight: bold;\n" + \
                  "        }\n" + \
                  "        p {\n" + \
                  "            font-size: 16px;\n" + \
                  "            line-height: 1.5;\n" + \
                  "        }\n" + \
                  "        .footer {\n" + \
                  "            margin-top: 20px;\n" + \
                  "            font-size: 14px;\n" + \
                  "            color: #888;\n" + \
                  "        }\n" + \
                  "        table {\n" + \
                  "            width: 100%;\n" + \
                  "            border-collapse: collapse;\n" + \
                  "            margin-bottom: 20px;\n" + \
                  "        }\n" + \
                  "        th, td {\n" + \
                  "            border: 1px solid #ddd;\n" + \
                  "            padding: 8px;\n" + \
                  "            text-align: left;\n" + \
                  "        }\n" + \
                  "        th {\n" + \
                  "            background-color: #f2f2f2;\n" + \
                  "        }\n" + \
                  "    </style>\n" + \
                  "</head>\n" + \
                  "<body>\n" + \
                  "    <div class=\"container\">\n" + \
                  "        <h1>{}</h1>\n".format(assunto_email) + \
                  "        <p>Olá " + nome_cliente + ",</p>\n" + \
                  "        <p>Abaixo estão os detalhes do seu pedido:</p>\n" + \
                  "        <table>\n" + \
                  "            <tr>\n" + \
                  "                <th>Produto</th>\n" + \
                  "                <th>Preço</th>\n" + \
                  "                <th>Quantidade</th>\n" + \
                  "                <th>Total</th>\n" + \
                  "            </tr>\n" + \
                  produtos_html + \
                  "            <tr>\n" + \
                  "                <td colspan=\"3\" style=\"text-align: right;\"><strong>Total do Pedido:</strong></td>\n" + \
                  f"                <td><strong>R$ {total_pedido:,.2f}</strong></td>\n" + \
                  "            </tr>\n" + \
                  "        </table>\n" + \
                  "        <p>Agradecemos por comprar conosco!</p>\n" + \
                  "        <div class=\"footer\">\n" + \
                  "            <p>Atenciosamente,<br>Equipe FIAP E-commerce</p>\n" + \
                  "        </div>\n" + \
                  "    </div>\n" + \
                  "</body>\n" + \
                  "</html>"

    return assunto_email, corpo_email

