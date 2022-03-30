# 百分之一百成功率的多线程复合翻译器
多线程复合翻译
* 何为多线程 使用多线程发起html翻译请求
* 何为复合 使用多种网页翻译器，避免了同一时间内发起过多请求被反爬虫拦截
* 何为100%成功率 在降低同服务器请求频率下 将句子编码成小于5000一组，提高效率；对于所有服务器不可用的情况。有huggingFace的强大翻译模型提供支持

支持en ==> zh

# 安装
见import模块

# 使用
```
c = CompositeTranslate().run(['red','blue','yellow'])
for i in c:
    print(i)
```

------------------
# MultiThreaded_Composite_Translate_100perCentSuccessRate
* What is multi-threading Use multiple threads to initiate html translation requests
* What is composite Using multiple web translators to avoid anti-crawlers intercepting too many requests launched at the same time
* What is a 100% success rate Encoding sentences into groups of less than 5000 with reduced frequency of requests from the same server increases efficiency; for cases where all servers are unavailable. Supported by huggingFace's powerful translation model

Support for en ==> zh

# install
See import module

# use
```
See section above
```

-------------------------------------
# See also/Borrowing
* all translate https://github.com/UlionTse/translators
* youdao google https://github.com/Chinese-boy/Many-Translaters
* baidu https://github.com/zachitect/B_Translate/blob/master/BD_Trans_Tool_v1.00.py
* huggingface https://huggingface.co/Helsinki-NLP/opus-mt-en-zh

# Please come and see my other projects
* Format-conversion-of-in-memory-audio
>A simple tool class to compensate for the extremely slow loading of librosa, the inability to convert soundfiles to raw, and the difficulty of using wave
>https://github.com/JyzjYzjyZ/Format-conversion-of-in-memory-audio
* AutoViedoSubtitleGenerator
>Using all the above techniques | as so as title
>https://github.com/JyzjYzjyZ/AutoViedoSubtitleGenerator
