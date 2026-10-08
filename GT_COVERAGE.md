# Ground-truth figures protected by printed-total checks

A figure is covered when it is the total or a component of a printed total (same column) whose components are listed and reconcile. Written by `tools/gt_coverage.py`.

| Statement pages | Figures | Covered | Share |
|---|---:|---:|---:|
| text layer | 3,325 | 3,244 | 97.6% |
| images in a digital PDF | 3,684 | 3,557 | 96.6% |
| fully scanned | 1,050 | 1,014 | 96.6% |
| **all** | **8,059** | **7,815** | **97.0%** |

Not covered: 244 figures. By statement type: other 84, income 68, financial_position 32, income_and_comprehensive_income 22, comprehensive_income 18, cash_flows 14, changes_in_equity 4, changes_in_net_assets 2. By row kind: item 240, subtotal 4.

Not checked by arithmetic at all: the line and period under which a figure is recorded. Two components swapped between lines still add up to their total, so placement in the ground truth rests on the cell-by-cell verification against the page images.
