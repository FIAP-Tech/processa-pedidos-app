import json
import boto3
import datetime
import requests

sqs = boto3.client('sqs')
queue_url_processa_entregas = 'https://sqs.us-east-1.amazonaws.com/672291737467/processa_entregas'
queue_url_envia_emails = 'https://sqs.us-east-1.amazonaws.com/672291737467/envia-emails'

def lambda_handler(event, context):
    envia_para_fila_processa_pedidos = False
    status_pedido = "PAGAMENTO_EFETUADO"
    assunto_email = "Pagamento efetuado com sucesso"
    sqs_message = json.loads(event['Records'][0]['body'])
    forma_pagamento = sqs_message.get('formaPagamento')

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
                assunto_email = "Falha ao processar pagamento"
                status_pedido = "FALHA_NO_PAGAMENTO"

    if envia_para_fila_processa_pedidos:
        sqs.send_message(
            QueueUrl=queue_url_processa_entregas,
            MessageBody=json.dumps(sqs_message)
        )

    pedido_id = sqs_message.get('idPedido')
    url = f"https://pedidos-app-step4-4a5a9f7b65f6.herokuapp.com/api/pedidos/{pedido_id}/status?status={status_pedido}"
    requests.patch(url)

    email_payload = {
        "emailDestinatario": sqs_message.get('cliente', {}).get('email'),
        "assunto": assunto_email,
        "corpoEmail": "teste corpo email"
    }

    sqs.send_message(
        QueueUrl=queue_url_envia_emails,
        MessageBody=json.dumps(email_payload)
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Processamento de pedidos concluído com sucesso!')
    }