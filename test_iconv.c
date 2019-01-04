#include <iconv.h>
#include <string.h>
#include <stdio.h>

int main() {
    /* 目的编码, TRANSLIT：遇到无法转换的字符就找相近字符替换
     *            IGNORE    ：遇到无法转换字符跳过*/
    //char *encTo = "UNICODE//TRANSLIT";
    const char* encTo = "UTF8//IGNORE";
    /* 源编码 */
    const char* encFrom = "BIG5";
    printf("%s->%s\n", encFrom, encTo);

    /* 获得转换句柄
     *@param encTo 目标编码方式
     *@param encFrom 源编码方式
     *
     * */
    iconv_t cd = iconv_open(encTo, encFrom);
    if (cd == (iconv_t)-1)
    {
        perror ("iconv_open");
        return 1;
    }

    /* 需要转换的字符串 */
    char inbuf[1024] = "\xbds\xbdX\xb4\xfa\xb8\xd5";  // "編碼測試"
    size_t srclen = strlen(inbuf);
    /* 打印需要转换的字符串的长度 */
    printf("srclen=%d\n", srclen);
    int i;
    for (i=0; i<strlen(inbuf); i++)
    {
        printf("%02x ", (unsigned char)inbuf[i]);
    }
    printf("\n");

    /* 存放转换后的字符串 */
    size_t outlen = 1024;
    char outbuf[outlen];
    memset(outbuf, 0, outlen);

    /* 由于iconv()函数会修改指针，所以要保存源指针 */
    char* srcstart = inbuf;
    char* tempoutbuf = outbuf;

    /* 进行转换
     *@param cd iconv_open()产生的句柄
     *@param srcstart 需要转换的字符串
     *@param srclen 存放还有多少字符没有转换
     *@param tempoutbuf 存放转换后的字符串
     *@param outlen 存放转换后,tempoutbuf剩余的空间
     *
     * */
    size_t ret = iconv(cd, &srcstart, &srclen, &tempoutbuf, &outlen);
    if (ret == -1)
    {
        perror ("iconv");
        return 1;
    }
    printf("srclen=%d, outbuf=%s\n", srclen, outbuf);
    for (i=0; i<strlen(outbuf); i++)
    {
        printf("%02x ", (unsigned char)outbuf[i]);
    }
    printf("\n");
    /* 关闭句柄 */
    iconv_close(cd);

    return 0;
}
