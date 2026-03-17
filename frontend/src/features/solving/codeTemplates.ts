import type { SubmissionLanguage } from "../../api/types";

const PYTHON_TEMPLATE = `def main() -> None:
    # TODO: write your solution here
    pass


if __name__ == "__main__":
    main()
`;

const CPP_TEMPLATE = `#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // TODO: write your solution here

    return 0;
}
`;

export function getSolutionTemplate(language: SubmissionLanguage): string {
  switch (language) {
    case "python":
      return PYTHON_TEMPLATE;
    case "cpp":
      return CPP_TEMPLATE;
    default:
      return PYTHON_TEMPLATE;
  }
}

export function getLanguageLabel(language: SubmissionLanguage): string {
  switch (language) {
    case "python":
      return "Python 3";
    case "cpp":
      return "C++17";
    default:
      return language;
  }
}