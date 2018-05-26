/*
 * To try this example, just compile it:
 * gcc -o example example.c
 *
 * and run it:
 * ./example
 * -- Testsuite PASSED, 2 out of 2 tests run --
 */

#include "mut.h"


TESTSUITE_BEGIN

TEST_BEGIN ("trivial test")

    CHECK(2 + 2 == 4);
    
TEST_END

TEST_BEGIN ("trivial test 2")

    FAIL_IF(2 + 3 == 4);
    
TEST_END

TESTSUITE_END


