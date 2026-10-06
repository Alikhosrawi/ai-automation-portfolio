# AI automation portfolio: one chore, gone

Small, real workflows built with AI, each removing one repetitive admin chore, with what broke and how I fixed it.

I'm [Ali Khosravi](https://github.com/Alikhosrawi), and I build these as personal learning projects, with AI as my co-pilot. Each folder is one working demo: the workflow file, fake sample data, screenshots, and a build story about what broke and how I fixed it.

The idea behind the series is simple: pick one chore, like sending reminders or chasing replies, and build the smallest thing that makes it go away. No big platform, just one fix for one job.

## Demos

| Demo | The chore it removes | Tools | Status |
|---|---|---|---|
| [Pipeline hygiene check](crm-pipeline-hygiene/) | Cleaning a HubSpot export before the Monday forecast call: finding duplicate deals (including messy ones an AI judges), deals with no activity or no amount, and showing the Q4 forecast before and after cleaning, with one to-do message per rep | n8n, AI, Python, CSV | Working demo on fake data (changes nothing in HubSpot, sends nothing), with a pre-registered planted-error test and 6 look-alike traps |
| [Physio appointment reminders](physio-appointment-reminders/) | Messaging tomorrow's patients one by one, answering "yes" / "can I move it?" replies, and following up with same-day no-shows | n8n, CSV | Working demo on fake data (sends nothing) |
| [Expat onboarding autopilot](expat-onboarding-autopilot/) | Building a document checklist for each new relocation client, chasing missing documents without nagging, and writing weekly updates for the client and their HR contact | n8n, CSV | Working demo on fake data (sends nothing) |
| [Physio supplies reorder agent](physio-supplies-reorder/) | Counting the supply cupboard every Friday, guessing next week's usage from the bookings, and preparing the order for each supplier for the practice manager to approve, without running out mid-week or overfilling the shelf | n8n, CSV | Working demo on fake data (orders nothing), with a pre-registered backtest on a synthetic 50-week history (41 weeks scored) |

**Coming next:** more builds, one chore at a time.

## All demos use fake data

Every name, phone number, email address and business here is made up. Phone numbers look like `+49 000 0000 0001`, emails like `patient1@example.com` and company domains end in `.example`, so none of them can reach a real person. The demos don't send anything either: messages are written to a "would send" log file so you can see exactly what would have gone out.

## How to use a workflow

You need a running copy of [n8n](https://n8n.io) (the free self-hosted version is enough).

1. Download the `.json` file from the demo's `workflow/` folder.
2. In n8n, open **Workflows → Import from File** (on a new, empty workflow: the **⋯** menu at the top right → **Import from File**) and pick the file.
3. Follow the setup steps in that demo's README. Usually that means putting the sample data where n8n can read it and checking the file paths.
4. Click **Execute workflow** and look at the output. If the workflow has several triggers, first pick its test button in the small menu next to **Execute workflow** (the demo README says which one).

The workflows contain no credentials, accounts or API keys. If you take one further, you add your own.

## Repo layout

```
ai-automation-portfolio/
├── README.md
├── LICENSE
├── crm-pipeline-hygiene/
│   └── (same layout, plus prompts/ for the two AI prompts and test/: the
│        pre-registered planted-error test, its answer key and results)
├── physio-appointment-reminders/
│   ├── README.md          what it does and how to try it
│   ├── build-story.md     how it was built, the bug, the fix
│   ├── workflow/          the n8n workflow (import this)
│   ├── data/              fake sample data + example output
│   └── screenshots/
├── expat-onboarding-autopilot/
│   └── (same layout)
└── physio-supplies-reorder/
    └── (same layout; two workflows: reorder agent + manager review,
         plus backtest/: the pre-registered re-test, its data and results)
```

## License

[MIT](LICENSE). Use anything here, at your own risk.
