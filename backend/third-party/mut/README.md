# Mut: a micro unit-testing framework

Mut is a minimalistic unit testing framework for C/Unix. It is designed to
fulfill the unit testing needs of a small library project, when the hassle of
integrating a more complete framework with its dependencies may not be justified.

It offers:

* Structure: test case identification and separation.
* Explicit assertions: `CHECK`, `FAIL_IF`
* Crash capture by handling `SIGSEV` signals.
* Basic reporting: fail/pass status and test case counters.

Mut is provided as a single header file to simplify integration. Just some
basic build rules in your makefiles will get you going.

## Limitations

Mut was developed on Linux with gcc, and has some Unix'isms (signal handling)
and gcc'isms (local lables). Some porting effort might be needed to work with other compilers.
If you happen to port Mut to other environments, portability patches are welcomed!

## Usage

In order to use this unit testing framework you just need to include the
header file. Mut test modules have the following structure:

```
#include <mut.h>
#include <your_library.h>

TESTSUITE_BEGIN

TEST_BEGIN("trivial test")
...
CHECK( 2 + 2 == 4 );
...
TEST_END


TEST_BEGIN("other test")
TEST_DISABLE
...
FAIL_IF( 2 + 2 != 4 );
...
TEST_END


TESTSUITE_END
```

Test code is written in regular C.

`TESTSUITE_BEGIN` and `TESTSUITE_END` macros are required and provide a main
C function with the necessary structure to execute your tests and report
results. By compiling this module and linking to the library under test
you'll get an executable that will run all tests defined from start to
finish and generate a final report on screen.

```
-- Testsuite PASSED, 52 out of 52 tests run --
```

`TEST_BEGIN` and `TEST_END` serve the purpose of delimiting and naming your
test code. This allows the framework to help you identifying the failing
functionality.

```
Error: Test "set_version() rejects void input" failed at line 412
-- Testsuite FAILED, 36 out of 52 tests run --
```

`CHECK()` and `FAIL_IF()` are the assertion macros available in Mut. They
are used to explicitly state conditions that have to be verified.

`TEST_DISABLE` can be used immediately after a `TEST_CASE()` declaration
to quickly disable a test case (useful for debugging).
