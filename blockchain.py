# {
#     "index": 0,
#     "timestamp": "",
#     "transactions": {
#         {
#             "sender": "",
#             "recipient": "",
#             "amount": 5,
#         }
#     },
#     "proof": "",
#     "previous_hash": "",
#
# }
import hashlib
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import json, Flask, request
from flask.json import jsonify
from argparse import ArgumentParser


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        self.new_block(proof = 100,previous_hash = 1)

    def register_node(self, address: str):                            # http://127.0.0.1:5001
        parsed_url = urlparse(address)                                  # 将地址解析
        self.nodes.add(parsed_url.netloc)                               # netloc中存的是127.0.0.1:5000

    def valid_chain(self,chain) -> bool:
        last_block = chain[0]                                           # 先取第一个
        current_index = 1

        while current_index < len(chain):                               # 遍历这个链条
            block = chain[current_index]

            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True







    def resolve_conflicts(self) -> bool:
        neighbours = self.nodes                                          # 拿到节点信息
        max_length = len(self.chain)
        new_chain = None

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')                         #请求邻居节点的区块链信息
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return  False





    def new_block(self, proof, previous_hash = None):

        block = {
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.last_block)
        }

        self.current_transactions = []
        self.chain.append(block)

        return block

    def new_transactions(self, sender, recipient, amount) ->int:
        self.current_transactions.append(
            {
                'sender' : sender,
                'recipient' : recipient,
                'amount' : amount
            }
        )

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(block_string).hexdigest()


    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        proof = 0
        while self.valid_proof(last_proof,proof) is False:              # 满足返回proof，不满足proof+1继续判断
            proof += 1

        return proof



    def valid_proof(self, last_proof: int, proof: int) -> bool:         # 用于验证与上一个proof运算后是否满足条件
        guess = f'{last_proof}{proof}'.encode()                         # 转换为字节数组
        guess_hash = hashlib.sha256(guess).hexdigest()
        if guess_hash[0:4] == '0000':
            return True
        else:
            return False

app = Flask(__name__)                                                   # 初始化一个Flask类

blockchain = Blockchain()

node_identifier = str(uuid4()).replace('-', '')                         # 用uuid生成一个字符串，作为发送的地址

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ["sender", "recipient", "amount"]
    if values is None:
        return "Missing values", 400

    if not all(k in values for k in required):                          # 如果有values有一个字段不在required中，就返回错误
        return "Missing values", 400

    index = blockchain.new_transactions(
        values['sender'],
        values['recipient'],
        values['amount']
    )

    response = {"message":f'Transactions will be added to Block {index}'}
    return jsonify(response), 201






@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block                                 # 取上个区块的信息
    last_proof = last_block['proof']                                   # 取上个区块的工作量证明
    proof = blockchain.proof_of_work(last_proof)
    blockchain.proof_of_work(last_proof)

    blockchain.new_transactions(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    block = blockchain.new_block(proof, None)                          # 新建区块

    #将信息打包返回

    response = {
        "message" : "New Block Forged",
        "index" : block['index'],
        "transactions" : block['transactions'],
        "proof" : block['proof'],
        "previous_hash" : block['previous_hash']
    }

    return jsonify(response), 200








@app.route('/chain',methods=['GET'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }
    return jsonify(response), 200                                       # 将json转成字符串








@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get("nodes")

    if nodes is None:
        return "Error: Please supple a valid list of nodes", 400
    for node in nodes:                                                  #将每个节点注册
        blockchain.register_node(node)

    response = {
        "message": "New Nodes have been added",
        "total_nodes": list(blockchain.nodes)                           # 将集合转换为list
    }
    return jsonify(response), 201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message' : 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200



if __name__ == '__main__':                                              # 将Flask这个框架启动，提供一个运行的入口
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
    args = parser.parse_args()                                          #解析
    port = args.port

    app.run(host='0.0.0.0', port=port)









