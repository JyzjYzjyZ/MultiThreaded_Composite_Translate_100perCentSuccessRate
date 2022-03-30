import http.client
import hashlib
import time
import urllib.parse
import random
import json
import copy
import urllib.request
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer ,MarianTokenizer
import execjs
import threading
import  translators  as  ts


class CompositeTranslate():
    def encode(sentences: list, max_len=4800):
        '''
        :param sentences: [sentence1,sentence2,...]
        :param max_len: The maximum length after encoding is generally much less than this value
        :return:[sentence1+sentence2,sentence3+sentence4+sentence5,...]
        '''

        def _getListLen(l):
            le = 0
            for c in l:
                le += len(c)
            return le

        def _chagesentences(sentences, max_len):
            temp = []
            clear = []
            for sentence in sentences:
                # 放进去以后的长度
                if len(sentence) + _getListLen(temp) + len(temp) * 2 > max_len:
                    clear.append(temp)
                    temp = [sentence]
                else:
                    # 能够放进去
                    temp.append(sentence)

            if temp != []:
                clear.append(temp)
            return clear

        def _change_to_list(clearList):
            def del_by_index_from_string(s, i):
                res = ''
                if i >= len(s):
                    raise IndexError('Subscripts out of bounds')
                index = -1
                for c in s:

                    index += 1
                    if index == i:
                        continue
                    res += c
                return res

            arr = copy.copy(clearList)
            for y in range(len(arr)):
                for x in range(len(arr[y])):
                    arr[y][x] = [arr[y][x]]
            for i in range(len(arr)):
                c = arr[i]
                c = str(c).replace('["', '[').replace('"]', ']').replace("['", '[').replace("']", ']').replace(
                    '], ', ']')
                c = c[1:-1]
                # c = del_by_index_from_string(c,1)
                # c = del_by_index_from_string(c,-2)
                arr[i] = c
            return arr

        res = _chagesentences(sentences, max_len)
        return _change_to_list(res)

    def decode(sentences: str):
        '''
        :param sentences:[sentence1+sentence2,sentence3+sentence4+sentence5,...]
        :return: [sentence1,sentence2,...]
        '''
        arr = copy.copy(sentences)
        res = []
        for i in range(len(arr)):
            # 最后一个】会分割出一个无效的
            res = res + arr[i].replace('[', '').split(']')[:-1]
        return res

    class CompositeTranslate_Multi_threaded():
        exitFlag = 0
        '''
        多线程的python翻译器
        只支持翻译列表形式的句子
        输入 单参数的翻译函数列表，一层列表嵌套表示当0不行是用1
        例 [0,1,2,3,4,[4.5,5.5],6,7,8]
        '''

        def __init__(self, sentences: list, functions: list):
            self._sentences = copy.deepcopy(sentences)
            self._fs = copy.deepcopy(functions)
            self.result = [None for x in range(len(self._sentences))]
            self._max_times = 3  # tqdm中的次数设置为 迭代次数+1
            self.times = 0

        class _Thread(threading.Thread):
            def __init__(self, function, kwargs):
                threading.Thread.__init__(self)
                self.func = function
                self.kw = kwargs
                self.start()
                self.join()

            def run(self):
                res = self.func(**self.kw)
                return res

        def _set_result(self, d):
            '''
            :param d:
            :return:
            '''

            def _rule(result):
                # 检查是不是中文
                if len(result) == 0: return False
                try:
                    return len([x for x in result if u'\u4e00' <= x <= u'\u9fff']) != 0
                except Exception as e:
                    print('_set_result', e)
                    return False

            def _try_translate(f, q, rule):
                # 这个是翻译一句
                if type(f) == int:
                    print('0')
                try:
                    result = f(q)
                    if rule(result) == False:
                        raise TypeError('Translated Result Error')
                except Exception as e:
                    print('_try_translate', e)
                    result = None

                return result

            sentence = d['sentence']
            i = d['sentence_i']

            f = d['f']
            f_i = d['f_i']
            fs_sub = d['fs_sub']

            if sentence == '':
                self.result[i] = ''
                return
            # 无论是否合适 全部添加 这里要求每个f都有q属性 并且配置好编解码 返回值为str or None
            self.result[i] = _try_translate(f=f, q=sentence, rule=_rule)
            # 如果返回值为None 认为该api 暂不可用 从fs中移除
            if self.result[i] == None or self.result[i] == '':
                if type(fs_sub) == list:
                    self._fs[f_i][0] = 0
                else:
                    self._fs[f_i] = 0
            return

        def _Multi_threaded_Composite_Translation(self):
            '''
            :return:null ==> 只更改self.result
            对已知为None的求解
            '''

            # 对于倒霉的 递归次数没用尽 却用尽翻译方法的 直接return 去离线翻译
            if len(self._fs) == 0:
                return

            f_i = -1
            link_list = []
            for i in [x for x in range(len(self.result)) if self.result[x] == None]:
                # 分配f
                ignore = 1
                fs = self._fs[:-ignore]  # 最后一个最为大保底
                f_i = f_i + 1 if f_i + 1 < len(fs) else 0
                fs_sub = fs[f_i]
                if type(fs_sub) == list:
                    # 对于有备选方案的 我不想写继承
                    f = fs_sub[0]
                else:
                    f = fs_sub
                sentence = self._sentences[i]
                dst = {
                    'f': f,
                    'f_i': f_i,
                    'fs_sub': fs_sub,
                    'sentence': sentence,
                    'sentence_i': i,
                }
                link_list.append(dst)

            for d in link_list:
                self._Thread(function=self._set_result, kwargs={'d': d})

            return

        def __iter__(self):
            return self

        def __next__(self):
            self.times += 1

            def del_all(l, t):
                def remove_all(list, t):
                    while t in list:
                        list.remove(t)
                    return list

                remove_all(l, t)
                list_index = [i for i in range(len(l)) if type(l[i]) == list]
                for i in list_index:
                    l_r = remove_all(l[i], t)
                    l[i] = l_r
                return l

            self._fs = del_all(self._fs, 0)

            while [] in self._fs:
                self._fs.remove([])

            # execution
            if None in self.result and self.times < self._max_times:
                self._Multi_threaded_Composite_Translation()
            elif None in self.result and self.times < self._max_times + 1:
                # 使用备选方案
                f = self._fs[-1]
                if __name__ == '__main__': print('=======================Machine Learning!============================')
                for i in [x for x in range(len(self.result)) if self.result[x] == None]:
                    self.result[i] = f(self._sentences[i])
            else:
                # 填充None
                raise StopIteration
            return self.result

    class Transklate_goodjin5():

        class _Yuguii():

            def __init__(self):
                self.ctx = execjs.compile("""
                function TL(a) {
                var k = "";
                var b = 406644;
                var b1 = 3293161072;

                var jd = ".";
                var $b = "+-a^+6";
                var Zb = "+-3^+b+-f";

                for (var e = [], f = 0, g = 0; g < a.length; g++) {
                    var m = a.charCodeAt(g);
                    128 > m ? e[f++] = m : (2048 > m ? e[f++] = m >> 6 | 192 : (55296 == (m & 64512) && g + 1 < a.length && 56320 == (a.charCodeAt(g + 1) & 64512) ? (m = 65536 + ((m & 1023) << 10) + (a.charCodeAt(++g) & 1023),
                    e[f++] = m >> 18 | 240,
                    e[f++] = m >> 12 & 63 | 128) : e[f++] = m >> 12 | 224,
                    e[f++] = m >> 6 & 63 | 128),
                    e[f++] = m & 63 | 128)
                }
                a = b;
                for (f = 0; f < e.length; f++) a += e[f],
                a = RL(a, $b);
                a = RL(a, Zb);
                a ^= b1 || 0;
                0 > a && (a = (a & 2147483647) + 2147483648);
                a %= 1E6;
                return a.toString() + jd + (a ^ b)
            };

            function RL(a, b) {
                var t = "a";
                var Yb = "+";
                for (var c = 0; c < b.length - 2; c += 3) {
                    var d = b.charAt(c + 2),
                    d = d >= t ? d.charCodeAt(0) - 87 : Number(d),
                    d = b.charAt(c + 1) == Yb ? a >>> d: a << d;
                    a = b.charAt(c) == Yb ? a + d & 4294967295 : a ^ d
                }
                return a
            }
            """)

            def getTk(self, text):
                return self.ctx.call("TL", text)

        def __init__(self,toLang='zh'):
            self._baidu_appid = '20190405000284840'
            self._baidu_secretKey = 'eYK0BQrpLj0tPtPppE32'
            self.fromLang = "auto"
            self.toLang = toLang

            self._youdao_data = {'from': self.fromLang, 'to': self.toLang, 'smartresult': 'dict',
                                 'client': 'fanyideskweb', 'salt': '1500092479607',
                                 'sign': 'c98235a85b213d482b8e65f6b1065e26', 'doctype': 'json', 'version': '2.1',
                                 'keyfrom': 'fanyi.web',
                                 'action': 'FY_BY_CL1CKBUTTON', 'typoResult': 'true'}  # , 'i': q

            self._google_js = self._Yuguii()

            self._huggingFace_path = r'./models\Helsinki-NLPopus-mt-en-zh'
            self._huggingFace_model = AutoModelForSeq2SeqLM.from_pretrained(self._huggingFace_path)
            self._huggingFace_tokenizer = MarianTokenizer.from_pretrained(self._huggingFace_path)
            self._huggingFace_num_beams = 4

        # =====================================================================
        # from  :https://github.com/zachitect/B_Translate/blob/master/BD_Trans_Tool_v1.00.py
        def baiduTranslate(self, q):

            httpClient = None
            myurl = '/api/trans/vip/translate'
            salt = random.randint(32768, 65536)
            sign = self._baidu_appid + q + str(salt) + self._baidu_secretKey
            m1 = hashlib.md5()
            m1.update(sign.encode())
            sign = m1.hexdigest()
            myurl = myurl + '?appid=' + self._baidu_appid + '&q=' + urllib.parse.quote(
                q) + '&from=' + self.fromLang + '&to=' + self.toLang + '&salt=' + str(salt) + '&sign=' + sign
            result = ""
            httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
            httpClient.request('GET', myurl)
            response = httpClient.getresponse()
            result = response.read()
            if httpClient:
                httpClient.close()

            return json.loads(result)['trans_result'][0]['dst']


        # =====================================================================
        # https: // github.com / Chinese - boy / Many - Translaters
        def youdaoTranslate(self, q):
            data = self._youdao_data
            data['i'] = q

            data = urllib.parse.urlencode(data).encode('utf-8')
            wy = urllib.request.urlopen(
                'http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule&sessionFrom=https://www.baidu.com/link',
                data)
            html = wy.read().decode('utf-8')
            ta = json.loads(html)
            return ta['translateResult'][0][0]['tgt']

        def googleTranslate(self, q):
            '''
            :param q:
            :return:
            '''

            '''
            使用例
            js = _Yuguii()
            tk = js.getTk(q)
            translate(q, tk)
            '''

            if len(q) > 4891:
                print("String out of bounds Please reduce the value of max_len in the config！")
                return

            q = urllib.parse.quote(q)

            url = "http://translate.google.cn/translate_a/single?client=t" \
                  "&sl=" + self.fromLang + "&tl=zh-CN&hl=zh-CN&dt=at&dt=bd&dt=ex&dt=ld&dt=md&dt=qca" \
                                           "&dt=rw&dt=rm&dt=ss&dt=t&ie=UTF-8&oe=UTF-8&clearbtn=1&otf=1&pc=1" \
                                           "&srcrom=0&ssel=0&tsel=0&kc=2&tk=%s&q=%s" % (self._google_js.getTk(q), q)

            # 我记得好像还有一个可以随机地址的来自
            def open_url(url):
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
                req = urllib.request.Request(url=url, headers=headers)
                response = urllib.request.urlopen(req)
                data = response.read().decode('utf-8')
                return data

            result = open_url(url)

            end = result.find("\",")
            if end > 4:
                return result[4:end]
            else:
                raise Exception('Error :googleTranslate')
            # =====================================================================

        # =====================================================================
        # https://huggingface.co/docs/transformers/quicktour
        # https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
        def huggingFaceTranslate(self, q):
            inputs = self._huggingFace_tokenizer(q, return_tensors="pt", )

            outputs = self._huggingFace_model.generate(inputs["input_ids"], num_beams=self._huggingFace_num_beams,
                                                       early_stopping=False)
            res = self._huggingFace_tokenizer.decode(outputs[0])
            return res

    def __init__(self):
        # 其中有道2 谷歌2 和huggingface 输出无法更改为zh
        self.targetLan = 'zh'
        tg = self.Transklate_goodjin5(self.targetLan)
        def _randomSleep(a,b):
            time.sleep(random.randint( int(a*10),int(b*10) )/10)
        def deepl(q):
            _randomSleep(0.7,1.1)
            return ts.deepl(q,to_language=self.targetLan)
        def alibaba(q):
            _randomSleep(0.3,0.5)
            return ts.alibaba(q,to_language=self.targetLan)
        def baidu_0(q):
            _randomSleep(0.4,0.6)
            return ts.baidu(q,to_language=self.targetLan)
        def baidu_1(q):
            _randomSleep(0.3,0.5)
            return  tg.baiduTranslate(q)
        def bing(q):
            _randomSleep(0.1,0.2)
            return ts.bing(q,to_language=self.targetLan)
        def youdao_0(q):
            _randomSleep(0.4,0.6)
            return ts.youdao(q,to_language=self.targetLan)
        def youdao_1(q):
            _randomSleep(0.4,0.6)
            return tg.youdaoTranslate(q)
        def google_0(q):
            _randomSleep(0.1,0.2)
            return ts.google(q,to_language=self.targetLan)
        def google_1(q):
            _randomSleep(0.1,0.2)
            return tg.googleTranslate(q)
        def sogou(q):
            _randomSleep(0.6,0.8)
            return ts.sogou(q,to_language=self.targetLan)
        def tencent(q):
            _randomSleep(0.7,0.9)
            return ts.tencent(q,to_language=self.targetLan)
        def caiyun(q):
            _randomSleep(0.5,0.7)
            return ts.caiyun(q,to_language=self.targetLan)
        def yandex(q):
            return ts.yandex(q,to_language=self.targetLan)
        def iflytek(q):
            return ts.iflytek(q,to_language=self.targetLan)
        def huggingface(q):
            q = self.decode(q)
            return tg.huggingFaceTranslate(q)
        # self.func = [[ts.deepl], [ts.alibaba], [ts.baidu, tg.baiduTranslate], ts.bing, [ts.youdao, tg.youdaoTranslate],
        #        [ts.google, tg.googleTranslate], ts.sogou, ts.tencent, ts.caiyun, ts.yandex, ts.iflytek,tg.huggingFaceTranslate]
        self.func = [
            deepl,alibaba,[baidu_0,baidu_1],bing,[youdao_0,youdao_1],
            [google_0,google_1],sogou,tencent,caiyun,huggingface
                        ]


    def run(self,sentences):
        for c in self.CompositeTranslate_Multi_threaded(sentences,self.func):
            pass
        if "[" in c:
            res = []
            for x in c:
                res.append(self.decode(x))
            return res
        else:
            return c



c = CompositeTranslate().run(['red','blue','yellow'])
for i in c:
    print(i)
