import math
import sys


REL_TOL = 1e-9
ABS_TOL = 1e-12


def validate(expected, result):
    absolute_error = abs(result - expected)

    if expected != 0:
        relative_error = absolute_error / abs(expected)
    else:
        relative_error = absolute_error

    correct = math.isclose(
        result,
        expected,
        rel_tol=REL_TOL,
        abs_tol=ABS_TOL
    )

    return {
        "correct": correct,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
    }


def main():

    if len(sys.argv) != 3:
        print(
            "Uso: python3 scripts/numeric_validator.py "
            "<expected> <result>"
        )
        sys.exit(1)

    expected = float(sys.argv[1])
    result = float(sys.argv[2])

    validation = validate(
        expected,
        result
    )

    print("==============================")
    print("NUMERIC VALIDATOR")
    print("==============================")

    print(f"Expected: {expected:.17g}")
    print(f"Result:   {result:.17g}")

    print(
        f"Absolute error: "
        f"{validation['absolute_error']:.12e}"
    )

    print(
        f"Relative error: "
        f"{validation['relative_error']:.12e}"
    )

    print(f"REL_TOL: {REL_TOL}")
    print(f"ABS_TOL: {ABS_TOL}")

    print()

    if validation["correct"]:
        print("CORRECT")
    else:
        print("INCORRECT")


if __name__ == "__main__":
    main()
