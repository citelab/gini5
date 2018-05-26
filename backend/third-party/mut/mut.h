/* -------------------------------------------------------------------------- */
/*                                                                            */
/*                        Micro Unit Testing Framework                        */
/*                  Copyright (c) 2009, Anton Gomez Alvedro                   */
/*                                                                            */
/* LICENSE                                                                    */
/*                                                                            */
/* Permission is hereby granted, free of charge, to any person obtaining a    */
/* copy of this software and associated documentation files (the "Software"), */
/* to deal in the Software without restriction, including without limitation  */
/* the rights to use, copy, modify, publish and distribute copies of the      */
/* Software, and to permit persons to whom the Software is furnished to do    */
/* so, subject to the following conditions:                                   */
/*                                                                            */
/* The above copyright notice and this permission notice shall be included in */
/* all copies or substantial portions of the Software.                        */
/*                                                                            */
/* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR */
/* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   */
/* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    */
/* THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER */
/* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    */
/* FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        */
/* DEALINGS IN THE SOFTWARE.                                                  */
/*                                                                            */
/* -------------------------------------------------------------------------- */



#include <stdio.h>
#include <stdlib.h>
#include <signal.h>



#ifndef __MUT_H__
#define __MUT_H__



#define TESTSUITE_BEGIN                                                        \
                                                                               \
    enum __veredict_t__ {                                                      \
        __V_FAILED__,                                                          \
        __V_UNDEFINED__,                                                       \
    };                                                                         \
                                                                               \
    enum __veredict_t__ __veredict__ = __V_UNDEFINED__;                        \
    int __total_tests__ = 0;                                                   \
    int __tests_run__ = 0;                                                     \
    char * __current_test_name__ = "undefined";                                \
                                                                               \
    void __sig_handler(int sig)                                                \
    {                                                                          \
        __veredict__ = __V_FAILED__;                                           \
        printf("Error: Test \"%s\" caused a Segmentation Fault!\n",            \
            __current_test_name__);                                            \
        printf("-- Testsuite FAILED, %d tests run --\n", __tests_run__);       \
        exit(1);                                                               \
    }                                                                          \
                                                                               \
    int main(void)                                                             \
    {                                                                          \
        signal(SIGSEGV, __sig_handler);                                        \



#define TESTSUITE_END                                                          \
    __testsuite_end__:                                                         \
        if(__veredict__ == __V_UNDEFINED__)                                    \
        {                                                                      \
            printf("-- Testsuite PASSED, %d out of %d tests run --\n",         \
                __tests_run__, __total_tests__);                               \
            return 0;                                                          \
        }                                                                      \
        else                                                                   \
        {                                                                      \
            printf("-- Testsuite FAILED, %d out of %d tests run --\n",         \
                __tests_run__, __total_tests__);                               \
            return 1;                                                          \
        }                                                                      \
    }



#define TEST_DISABLE goto __test_end_disabled__;



#define TEST_BEGIN(__test_name__)                                              \
        {                                                                      \
            __label__ __test_end__;                                            \
            __label__ __test_end_disabled__;                                   \
            __current_test_name__ = __test_name__;                             \
            __total_tests__++;                                                 \
                                                                               \
            if (__veredict__ == __V_UNDEFINED__)                               \
            {                                                                  \



#define TEST_END                                                               \
        __test_end__:                                                          \
            __tests_run__++;                                                   \
        __test_end_disabled__:                                                 \
            ;                                                                  \
            }                                                                  \
        }



#define __ASSERTION_FAILED__                                                   \
        __veredict__ = __V_FAILED__;                                           \
        printf("Error: Test \"%s\" failed at line %d\n",                       \
            __current_test_name__, __LINE__);                                  \
        goto __test_end__;



#define CHECK(__assertion__)                                                   \
    if ( !(__assertion__) )                                                    \
    {                                                                          \
        __ASSERTION_FAILED__                                                   \
    }



#define FAIL_IF(__assertion__)                                                 \
    if (__assertion__)                                                         \
    {                                                                          \
        __ASSERTION_FAILED__                                                   \
    }



#endif
