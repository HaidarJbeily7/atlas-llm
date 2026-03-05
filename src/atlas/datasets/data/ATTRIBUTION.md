# Dataset Attribution

The datasets in this directory are vendored from the **garak** LLM vulnerability scanner.

- **Source**: [garak](https://github.com/NVIDIA/garak) by NVIDIA Corporation
- **License**: Apache License 2.0
- **Original location**: `garak/data/` within the garak Python package

## Included Datasets

| Directory / File                 | Description                                      |
|----------------------------------|--------------------------------------------------|
| `dan/`                           | DAN / DUDE / STAN jailbreak prompt templates      |
| `donotanswer/`                   | DoNotAnswer refusal test prompts                  |
| `payloads/`                      | Harmful behaviors, SQL injection, XSS payloads    |
| `realtoxicityprompts/`           | RealToxicityPrompts continuation samples          |
| `xss/`                           | XSS attack payload templates and components       |
| `gcg/`                           | GCG adversarial suffixes                          |
| `packagehallucination/`          | Package name hallucination test data              |
| `inthewild_jailbreak_llms.json`  | In-the-wild jailbreak prompt collection           |

## License Notice

These datasets are redistributed under the terms of the Apache License, Version 2.0.
You may obtain a copy of the license at: https://www.apache.org/licenses/LICENSE-2.0

Copyright (c) NVIDIA Corporation. All rights reserved.
