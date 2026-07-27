┌─────────────────────────────────────────┐
│  Docker container: fitwise-db           │
│  ┌───────────────────────────────────┐  │
│  │  PostgreSQL                       │  │
│  │  database: fitwise                │  │
│  │                                   │  │
│  │  products  ← 50,244 rows          │  │
│  │  reviews   ← 433,735 rows         │  │
│  │  cart_items (empty)               │  │
│  └───────────────────────────────────┘  │
│         ↑                               │
│    port 5432                            │
└─────────┼───────────────────────────────┘
          │
   localhost:5432
          ↑
   Python script reads CSV → INSERT




   #############################

   User chat → POST /chat → run_agent  [@traceable]
                              │
                              ├── wrap_openai → Groq LLM  [auto-traced]
                              └── execute_tool              [optional @traceable]
                                        │
                                        ▼
                              LangSmith cloud dashboard