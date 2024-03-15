from flask import Flask, render_template, request, session, jsonify, redirect
from sql_config import User, Info, BasEle,db_session, InfoId
from flask_cors import CORS
import spacy
import json

from openai import OpenAI
client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    #GPT-4
    # api_key="sess-mq7xMO7fFmqHUA7P18BhMBURM1nRFBQvpQJ2EYPT",
    # # base_url="https://api.openai.com/"
    #GPT3.5
    #api_key="sk-kx0Llq2Xv124mqY5tlBHQ6Xs5995413MQzxRNJgxd0DY19tK",
    #base_url="https://api.chatanywhere.tech/v1"
)
from bs4 import BeautifulSoup
import requests

import paddle
paddle.enable_static()

import string
import jieba
import jieba.posseg as pseg
jieba.enable_paddle()  # 启动paddle模式

app = Flask(__name__)
CORS().init_app(app)
# 修改Jinja2变量插值的语法
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'

app.secret_key = 'jj'

# 加载spaCy的中文模型
nlp = spacy.load('zh_core_web_sm')

def analyze_sentence(sentence):
    # 使用模型对句子进行处理
    doc = nlp(sentence)

    # 初始化对象、特征和量值
    obj = None
    feature = None
    value = None

    # 遍历Doc对象中的每个Token
    for token in doc:
        # 如果Token的词性是名词，则将其作为对象
        if token.pos_ == 'NOUN':
            obj = token.text
        # 如果Token的词性是动词或形容词，则将其作为特征
        elif token.pos_ in ['VERB', 'ADJ']:
            feature = token.text
            # 将特征的程度作为量值
            value = token.head.text

    return obj, feature, value

#智能拓展
@app.route('/exnlp', methods=['GET', 'POST'])
def exnlp():
    if request.method == 'POST':
        prompt = request.form.get('question')
        messages = [{'role': 'user', 'content': prompt}]
        response = gpt_35_api_stream(messages)
        # 直接返回文本响应，而不是 JSON 对象
        return response
    else:
        info_class_id = request.args.get('id')  # 从URL参数中获取info_class_id
        with db_session():
            nodes = db_session.query(Info).filter(Info.info_class_id == info_class_id).all()  # 使用info_class_id查询Info表
            nodes_data = [{"id": node.id, "label": node.symbol} for node in nodes]
        print(nodes_data)  # 打印nodes_data
        return render_template('admin/exnlp.html',nodes_data=nodes_data)


def gpt_35_api_stream(messages: list):
    """为提供的对话消息创建新的回答 (流式传输)

    Args:
        messages (list): 完整的对话消息
    """
    # Ensure all 'content' fields are strings
    for message in messages:
        if message['content'] is None:
            message['content'] = ''
    stream = client.chat.completions.create(
        # model='gpt-4-turbo-preview',
        model='gpt-3.5-turbo',
        messages=messages,
        stream=True,
    )
    response = ""
    for chunk in stream:
        # print(chunk)  # 打印每个消息块以进行调试
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content
    # 替换掉 response 中的换行符和制表符
    response = response.replace('\n', ' ').replace('\t', ' ')
    return response

#自然语义模块
@app.route('/process_text', methods=['GET', 'POST'])
def process_text():
    results = {}  # 确保 results 始终被定义
    if request.method == 'POST':
        text = request.form.get('text', '请输入一段文字')
        # 删除所有中英文标点符号
        all_punctuations = string.punctuation + "。，“”‘’！？【】（）《》「」、"
        text = text.translate(str.maketrans('', '', all_punctuations))
        words = pseg.cut(text, use_paddle=False)  # paddle模式
        # 添加词性标注的含义
        pos_tags = {
            'n': '普通名词',
            'f': '方位名词',
            's': '处所名词',
            't': '时间',
            'nr': '人名',
            'ns': '地名',
            'nt': '机构名',
            'nw': '作品名',
            'nz': '其他专名',
            'v': '普通动词',
            'vd': '动副词',
            'vn': '名动词',
            'a': '形容词',
            'ad': '副形词',
            'an': '名形词',
            'd': '副词',
            'm': '数量词',
            'q': '量词',
            'r': '代词',
            'p': '介词',
            'c': '连词',
            'u': '助词',
            'xc': '其他虚词',
            'w': '标点符号',
            'PER': '人名',
            'LOC': '地名',
            'ORG': '机构名',
            'TIME': '时间'
        }
        for word, flag in words:
            tag = pos_tags.get(flag, "未知")
            if tag not in results:
                results[tag] = []
            results[tag].append(word)
        return jsonify(results)  # 返回一个 JSON 对象
    return render_template('/admin/nlp.html', results=results)

# 用户登录
@app.route('/', methods=['GET', 'POST'])
def indexadmin():
    return redirect('/login')


# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        session['user'] = None
        session['user_state'] = None
        return render_template('login.html')
    if request.method == 'POST':
        try:
            username = request.get_json()['username']
            password = request.get_json()['password']
            with db_session():
                result = db_session.query(User).filter(User.username == username).filter(
                    User.password == password).first()
                if result:
                    if result.state == '1':
                        session['user'] = result.username
                        session['user_state'] = result.state
                        return '1'
                    else:
                        return '3'
                else:
                    return '0'
        except:
            return '0'


# ----------------------------------------------------

# 用户管理
@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'GET':
        # 获取用户数据
        with db_session():
            userInfosDb = db_session.query(User).all()
        userInfos = []
        for i in userInfosDb:
            userInfos.append(
                {'username': i.username, 'password': i.password, 'state': i.state, 'id': i.id, 'name': i.name})

        userInfos.reverse()
        return render_template('/admin/user.html', userInfos=userInfos)


# 添加用户
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        try:
            username = request.get_json()['addUser']['username']
            password = request.get_json()['addUser']['password']
            state = request.get_json()['addUser']['state']
            name = request.get_json()['addUser']['name']
            with db_session():
                to_root = User(username=username, password=password, state=state, name=name)
                db_session.add(to_root)
                db_session.commit()
                return '1'
        except:
            return '0'


# 编辑用户
@app.route('/save_user', methods=['GET', 'POST'])
def save_user():
    if request.method == 'POST':
        try:
            username = request.get_json()['username']
            password = request.get_json()['password']
            state = request.get_json()['state']
            name = request.get_json()['name']
            id = request.get_json()['id']
            with db_session():
                result = db_session.query(User).filter(User.id == int(id)).first()
                result.username = username
                result.password = password
                result.state = state
                result.name = name
                db_session.commit()
            return '1'
        except:
            return '0'


# 删除用户
@app.route('/del_user', methods=['GET', 'POST'])
def del_user():
    if request.method == 'POST':
        try:
            id = request.get_json()['id']
            with db_session():
                result = db_session.query(User).filter(User.id == int(id)).first()
                db_session.delete(result)
                db_session.commit()
            return '1'
        except:
            return '0'


# ----------------------------------------------------
@app.route('/main', methods=['GET', 'POST'])
def main():
        return render_template('/login.html', user=session['user'])

# 基元管理
@app.route('/basic_element', methods=['GET', 'POST'])
def basic_element():
    if request.method == 'GET':
        # 获取用户数据
        with db_session():
            userBasEleDb = db_session.query(BasEle).all()
        BasEleList = []
        for i in userBasEleDb:
            BasEleList.append(
                {'name': i.name, 'class_': i.class_, 'info_text': i.info_text, 'time_': i.time_, 'id': i.id})

        BasEleList.reverse()
        return render_template('/admin/basele.html', BasEleList=BasEleList)


# 添加基元
@app.route('/add_basic_element', methods=['GET', 'POST'])
def add_basic_element():
    if request.method == 'POST':

        try:
            name = request.get_json()['infos']['name']
            class_ = request.get_json()['infos']['class_']
            info_text = request.get_json()['infos']['info_text']
            with db_session():
                to_root = BasEle(name=name, class_=class_, info_text=info_text)
                db_session.add(to_root)
                db_session.commit()
                return '1'
        except:
            return '0'


# 编辑基元分类
@app.route('/save_basic_element', methods=['GET', 'POST'])
def save_basic_element():
    if request.method == 'POST':
        try:
            name = request.get_json()['name']
            class_ = request.get_json()['class_']
            info_text = request.get_json()['info_text']
            time_ = request.get_json()['time_']
            id = request.get_json()['id']
            with db_session():
                result = db_session.query(BasEle).filter(BasEle.id == int(id)).first()
                result.name = name
                result.class_ = class_
                result.info_text = info_text
                result.time_ = time_
                db_session.commit()
            return '1'
        except:
            return '0'


# 删除基元
@app.route('/del_basic_element', methods=['GET', 'POST'])
def del_basic_element():
    if request.method == 'POST':
        try:
            id = request.get_json()['id']
            with db_session():
                result = db_session.query(BasEle).filter(BasEle.id == int(id)).first()
                db_session.delete(result)
                db_session.commit()
            return '1'
        except:
            return '0'


# 定义排序函数
def custom_sort(item):
    symbol = item['label']['符号']
    if symbol.startswith('M'):
        return (0, int(symbol[1:]))
    elif symbol.startswith('A'):
        return (1, int(symbol[1:]))
    else:  # 'R' 开头
        return (2, int(symbol[1:]))


# ---------------------------
# 基元管理
@app.route('/info/<id>', methods=['GET', 'POST'])
def info(id):
    if request.method == 'GET':
        info_class_id = id

        with db_session():
            result = db_session.query(Info).filter(Info.info_class_id == str(info_class_id)).all()
        infoslist = []
        toidlist = []

        for i in result:
            listInfosId = []
            # 寻找对于info id 的特征量值数据加入 List Dict
            infosId = db_session.query(InfoId).filter(InfoId.info_id == i.id).all()
            for iii in infosId:
                listInfosId.append({'特征': iii.chara, '量值': iii.value, 'id': iii.id})
            # todo 后端更新数据
            infoslist.append(
                {'id': i.id, 'label': {'类型': i.class_, '符号': i.symbol, '对象': i.obj_, 'infoid': listInfosId}})
            if i.info_id != '':
                toidlist.append({'from': i.id, 'to': i.info_id})

        # 重新排序
        sorted_data = sorted(infoslist, key=custom_sort)
        print(sorted_data)
        return render_template('/admin/info.html', info_class_id=info_class_id, toidlist=toidlist,
                               infoslist=sorted_data)

# 基元添加
@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    if request.method == 'POST':
        print(request.get_json())
        selecta = request.get_json()['selecta']
        name = request.get_json()['name']
        obj = request.get_json()['obj']
        mubiaoid = request.get_json()['mubiaoid']
        info_class_id = request.get_json()['info_class_id']

        if selecta == '物元':
            name = 'M' + name
        if selecta == '事元':
            name = 'A' + name
        if selecta == '关系元':
            name = 'R' + name

        with db_session():
            info = Info(class_=selecta, symbol=name, obj_=obj, info_id=mubiaoid,
                        info_class_id=info_class_id)
            db_session.add(info)
            db_session.commit()
        return '1'


# 添加基元id
@app.route('/add_info_id', methods=['GET', 'POST'])
def add_info_id():
    if request.method == 'POST':
        info_id = request.get_json()['to_start_id']
        chara = request.get_json()['tezheng']
        value = request.get_json()['va']
        with db_session():
            info = InfoId(info_id=info_id, chara=chara, value=value)
            db_session.add(info)
            db_session.commit()
        return '1'


# 删除基元id
@app.route('/del_info_id', methods=['GET', 'POST'])
def del_info_id():
    if request.method == 'POST':
        id = request.get_json()['id']
        with db_session():
            res_db = db_session.query(InfoId).filter(InfoId.id == int(id)).first()
            db_session.delete(res_db)
            db_session.commit()

        return '1'


# 删除基元
@app.route('/del_info', methods=['GET', 'POST'])
def del_info():
    if request.method == 'POST':
        try:
            id = request.get_json()['id']
            with db_session():
                result = db_session.query(Info).filter(Info.id == int(id)).first()
                db_session.delete(result)

                del_info_id = db_session.query(InfoId).filter(InfoId.info_id == int(id)).all()
                if del_info_id:
                    for info in del_info_id:
                        db_session.delete(info)
                db_session.commit()
            return '1'
        except:
            return '0'


# 编辑基元
@app.route('/save_info', methods=['GET', 'POST'])
def save_info():
    if request.method == 'POST':
        try:
            print(request.get_json())
            symbol = request.get_json()['fuhao']
            obj_ = request.get_json()['duixiang']
            id = request.get_json()['id']
            infoid = request.get_json()['infoid']
            with db_session():
                result = db_session.query(Info).filter(Info.id == int(id)).first()
                result.symbol = symbol
                result.obj_ = obj_

                if infoid:
                    for abc in infoid:
                        abc_db = db_session.query(InfoId).filter(InfoId.id == int(abc['id'])).first()
                        abc_db.chara = abc['特征']
                        abc_db.value = abc['量值']

                db_session.commit()
            return '1'
        except:
            return '0'




if __name__ == '__main__':
    print("基元库管理系统已打开,默认用户名密码为root root")
    app.run(debug=True)
