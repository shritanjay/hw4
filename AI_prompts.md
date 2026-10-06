# AI Prompts

For each Homework 4 problem, this file preserves the prompts I typed in my own words. The prompt text is stored verbatim as provided; only section labels, "What was lacking," and evidence notes are added around it. Each problem section includes its problem number and title.

## Background

These prompts set up the HW4 workspace. They are background rather than problem work.

What was lacking: workspace setup only; the project instructions are in Problem 1.

### Prompts

#### Background Prompt 1

I want to do homework 4 now. Can you save everything in that folder

#### Background Prompt 2

Everything we do now onwards, nothing of the past

#### Background Prompt 3

yes start AI_prompts.md so that everything goes there.

## Problem 1: Vibe coder prompts

These are the vibe coder prompts that describe the Campus Customs shop + chatbot build: goal, stack, features, data, research, and repo rules. Prompts 1–4 were typed before the section title (Prompt 5) and were moved here from Background on the user's instruction.

What was lacking: the prompts don't yet name the model, the account/login flow details (sign-up fields, sessions), how matching items appear on the page, or the agent's tools. Those will need follow-ups during the build.

### Prompts

#### Prompt 1

I will give you background now. So we need to build Campus Customs Shop and Chat bot. They need a real customer website with a helpful chatbot. Dont do anything just hear the contxt here.

#### Prompt 2

We need to build a React + vite typescript front end and a python Fast API backend. We need the brain to be a Pydantic AI agent. Shoppers should be able to browse products, create an account, chat about merch, see matching items appear on the page. And get honest ansers about price and stock from a local database.

#### Prompt 3

we are given campus_customs.db with tables for the product catalogue, inventory by size and users (with hased passwords). The image file paths are in the catalogue table. Research https://yalebulldogblue.com/ to know more about the style of Campus Customs page and information for your agent prompt.  Note that in the end we will push the project to a public GitHub repo and submit the repo URL on Canvas. do not commit the database or product images. I  downloaded the Zip file and saved it under HW4. Unzip it if you can

#### Prompt 4

okay perfect. and within the data/products/ the paths match the catalogue table


#### Prompt 5

Okay now we start with Problem 1: Vibe coder prompts.

#### Prompt 6

You have already done the AI_prompts.md creation. Just remeber that put one section for each problem. Each section must include the problem number nad title; at least one prompt that i typed and one follow up prompt if needed. If i miss that and we go to the next problem do let me know okay/.

#### Prompt 7

In problem 1  - i thought i gave you the instructions etc. And we have the title

## Problem 2: Analyze the database

What was lacking: nothing major. Field meanings saved to output/database_fields.md; tables, fields and why each matters started in output/harness.md.

### Prompts

#### Prompt 1

Awesome now we do problem 2: Analyze the database

#### Prompt 2

Tell me what each field of each table in the database data/campus_customs.db is about

#### Prompt 3

start the file output/harness.md. write down each table and the fields. Also give a short line on why each field matters for the shop or the chatbot.

## Problem 3: Build the Campus Customs website

What was lacking: products grid and single-item pages load from the database; floating chat panel is a stub (POST /api/chat echoes, no agent yet). Log in / Create account are still not wired to the backend. Home and About copy is paraphrased from yalebulldogblue.com, not copied.

### Prompts

#### Prompt 1

Now the Problem 3: Build the Campus Customs website.

#### Prompt 2

we want to generate a boiler plate/framework for React + Vite + TypeScript front end for Campus Customs. Lets put a nav bar at the top that links to the main pages: Home; Products; About Us; Log in; Create account.

#### Prompt 3

Pull the campus style wording from yalebulldogblude.com for Home and about us. Make sure to write these pages in your voice. I dont wnt exact copy of the orginal site text

#### Prompt 4

on the products oage show product images from the catalogue(use the image paths in the database) with basic info (name, price, short description. Make it in a way that each product opens a single-item page. Large image on one side, full product text on the other -description, price, sizes/stock when you have them. When clicking on products it should take the shooper there.

#### Prompt 5

Now add a chat interfact in the bottom right of the site. If it is a floating chat panel that is fine too. It does not need to talk to an agent yet. A stub that will call your backend later is fine for now.

#### Prompt 6

now we need a small API to read the database. It is fine to start a simple FastAPI app in backend/main.py to serve products and images. We will grow it into the agent backend in Problem 5.

## Problem 4: Create account and login

What was lacking: the first prompt did not specify password rules, sessions, or security level. The follow-up asked for secure storage; now 600k-iteration PBKDF2-SHA256 with a 16-byte salt per user, 8–128 char passwords, confirm must match, duplicate emails blocked, 5-failure lockout, no email enumeration, HttpOnly cookie session, and "Hi, first name / Log out" in the nav. Verified new accounts are inserted into the users table. Seed test user login failed at first (seed hashes use 120k iterations); fixed by checking both settings and upgrading old hashes on login, and confirmed in the browser. A brand-new account (Demo Shopper) was created, logged out, rejected with a wrong password, and logged back in through the UI; credentials kept in gitignored data/test_accounts.txt. harness.md section 3 now documents the full auth flow, stored fields, password protection, sessions, guessing protection, test evidence, and known limits.

### Prompts

#### Prompt 1

okay now lets go to problem 4: create account and login

#### Prompt 2

build a create-account/login flow. Make sure to have create account: first name, last name, email, password, and a confim password portion that confirms the typed password. Basically a user has to type the password 2 times for it to work. Then a login : email and password

#### Prompt 3

perfect. make sure that the new accounts go into the users table. Make sure to store passwords securely so hackers cannot access them

#### Prompt 4

okau perfect. now the seed database already had a test user. email: test@campuscustoms.yale.edu and password:password. Confirm that you can log in as that user.

#### Prompt 5

now confirm that a brand-new account that you create also works.

#### Prompt 6

update output/harness.md with how the authentication works. What you store for a user, how the passwords are protected, and anything else you think is required to be stored there.

## Problem 5: PydanticAI agent backend

What was lacking: the prompt did not name the model, the tools, or what "honest" checks to add. I used gpt-5.6-luna via Portkey (AGENTS.md), three read-only DB tools, structured ShopReply output with product ids validated against the DB, and cost limits. Testing found a sold-out-size bug (bot said an item was not carried); fixed in tools.py and the prompt. Chats are not yet saved to the chat_messages table. Follow-up added Campus Customs voice + safety basics (moved prompt to prompts/prompt.md), reorganized models.py (ProductCard, validated ChatRequest/ChatReply, ShopReply field descriptions), documented front end ↔ FastAPI and agent loading in harness.md, and verified uvicorn main:app --reload --port 8000 from backend/. Safety test caught a "add to cart" claim (no cart exists); fixed in the prompt.

### Prompts

#### Prompt 1

now lets go to problem 5: pydanticAI agent backend

#### Prompt 2

we need to build the shop chatbot as a PydanticAI agent behind FastAPI. We need to plug it into the front-end chat widget. Put the API app in backend/main.py. it is the file that you run with Uvicorn. Keep the agents as these 4 files next to it. : backend.prompt/prompt.md - system prompt; backend/agent.py - agent entry/wiring; backend/tools.py - tools the agent can call; backend/models.py - pydantic / pydanticAI structured types. In main.py expose a chat route so a message from the website returns a reply frmo the agent. And whatever else is needed for products/auth

#### Prompt 3

put campus customs voice and safety basics into prompts/prompt.md.  start or update types in models.py foor chat replies or product cards as needed. iN output/harness.md note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000

## Problem 6: Tools: product info and stock

What was lacking: did not say how to enforce "no invented numbers" or how exact stock answers should be. Added get_product_info (description + price) and a stronger check_stock (per-size counts, "sold out" / "only N left" labels, requested-size summary), a ModelRetry output validator that rejects prices or quantities not returned by a tool, bold sold-out wording in the prompt, and an offline test (961 tool-vs-DB checks). Live tests matched the DB; fixed a retries-argument crash and a colors misreading. Follow-up: prompt now has a "Which tool to call" table and step-by-step for price/stock questions; models.py gained SearchResult and NotFound return types; harness.md §5.3 explains every lookup field and why it was chosen.

### Prompts

#### Prompt 1

problem 6: tools: product info and stock

#### Prompt 2

the agent tools that look up real information from campus_customs.db: product description; price; how many are in stock (by size when the customer asks). The agent must use the database - it should not invent prices or quantities. if a size is out of stock, mention it clearly

#### Prompt 3

expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Make sure to add or update return types in models.py. In output/harness.md, list each tool and explain whcih model fields you chose for lookup results and why.

## Problem 7: Chat search that updates the page

What was lacking: didn't say where on the page the cards go, how many to show, or when NOT to update the page. I used a "From your chat" grid at the top of every page (up to 30 cards, replaced by each new search, with a Clear button), set only for browse-type questions, never for single-item or stock checks. Contract: agent returns ShopReply.page_results {title, product_ids}; backend keeps only ids returned by a search this turn and builds ProductCards from the DB into ChatReply.page. Also fixed raw Markdown in chat bubbles. Follow-up check: chat cards did open the detail page, but it rendered 4,435 px down under the results grid; fixed by collapsing the chat grid to a one-line bar on item pages and scrolling to top on every route change. Verified page cards, re-expanded cards, chat mini-cards, and the normal Products grid all open the detail view at the top. Follow-up 2: prompt.md Output format now explains where each field appears and that page_results show at the top of the current page; harness.md §6.3b shows the step-by-step path, a per-page table, and how long results last.

### Prompts

#### Prompt 1

Problem 7: Chat search that updates the page

#### Prompt 2

lets add a feature to the site, if a customer asks about a type of item. For example "what t shirts you have" the agent should search the catalogue and the website should dynamicaly show those matching items as product cards (image, name, price, short info). This is an API contract: the agent returns structured product matches and then the front end renders them on the website. It looks good!

#### Prompt 3

after the dynamic product cards are loaded by the new feature, make sure that the same single item page behaviour built in problem 3 still works: each product card including the ones the chat just put on the page should still open that detail view (i.e., large image + full info) when clicked.

#### Prompt 4

Update prompts/prompt.md and output/harness.md so it is clear how the search results reach each page.

## Problem 8: Customer memory

What was lacking: no limit on how much history to reload or send to the model, no rule on guests, and no way to clear history. I used the existing chat_messages table (memory.py), reload the last 50 in the widget and the last 10 for the agent, ignore browser history when logged in (DB is the source of truth), save nothing for guests, and added Clear history. Who is chatting (name, email, member since) and the page (path, product_id, results title) go into ShopDeps plus dynamic instructions, with tools get_customer_info, get_viewed_product, and get_past_recommendations. Verified "do you have this in pink?" on a product page, memory across logout/login, and reload in the browser. Follow-up: verified guests can chat (page context and in-session follow-ups work) and nothing is saved for them (chat_messages 30 → 30); harness.md §7 now has a guest vs logged-in table, a table of customer fields the agent does and does not see, and the step-by-step page-context path.

### Prompts

#### Prompt 1

Problem 8: Customer memory

#### Prompt 2

Note that we need to have chat history saved in the database in an appropriate table and reload when a shopper is logged in. The agent should know who is chatting (their name and email), and put that in the agent deps (or an equivalent clear patter) and tools the agent can call. Also pass enough page context that if someone is on a product page and they ask "do you have this in pink" the agent should know which item they mean. Note that you can put code into the agent context if required.

#### Prompt 3

okay make sure that guests can still chat, but historu is only needed to persist for logged-in users. after you make sure that. document in output/harness.md how the user chat history is stored, and what customer fields the agent sees, and how the page context is passed

## Problem 9: Usability improvements

What was lacking: the prompt left the choice of improvements open and gave no way to measure "faster or cheaper". I picked: (F1) size / in-stock / sort filters on Products with sizes on every card; (F2) page-aware chat quick replies, typing dots, Esc, full-screen on phones, redaction notice; (B1) per-turn audit + benchmark, name lookup in check_stock / get_product_info, a prompt half the size, tools offered only when useful — input tokens down 45% on a 6-question benchmark; (B2) card/SSN/password redaction before the model and DB, a sold-out-claim guard, and color families (testing found pink → dusty coral was being missed). Follow-up: output/usability.md explains each improvement (problem seen, what was added, why it helps the shopper and the business). It was written right after building, which the file notes.

### Prompts

#### Prompt 1

Problem 9: Usability improvements

#### Prompt 2

Now that the core shop works, we need to improve it. Choose and implement 2 front end usability improvements. and 2 agent/backend usability improvements. Essentially we want the site to look better and make it easier to use. and also want the backend to make sure that the agent output is better, more accurate and safer. feel free to make new agent tools or things that also make the agent overall run faster or cheaper.

#### Prompt 3

write output/usability.md before or as you build. For each of the improvements explain what you added. and why it helps a campus customs shopper or the business.

#### Prompt 4

i want to make sure all the improvements show up in the running app. how do i open it?

## Problem 10: Style the website

What was lacking: no exact palette, which departments to use, or whether the serif should cover body text; the Yale typeface itself is licensed and can't go in a public repo. Used Bulldog Blue layout in dark navy with Yale Blue #00356B, EB Garamond (closest free old-style serif) for headings, nav and prices, a text-built Yale tile thinking indicator, tees-first ordering, and five rule-based departments (incl. Grad & Professional Schools for SOM). Fixed two bugs found in testing: "Brooks Brothers" filed under Family, and all department nav links showing as active. Wrote output/design.md.

### Prompts

#### Prompt 1

okay it loosk good. Problem 10: Style the website

#### Prompt 2

Design things to do: match the Bulldog Blue site look but keep it dark. Keep the font type the same as the font in the Yale logo. the chat feel instead of having ... when the AI is thinking lets have a yale logo there thingking/loading. the hierarchy of products lets have tees first after all. i think it is better as it is cheaper. we can also have some departmetns under the "all" products since there are so many? So we should be able to filter using department. for example there are general, there are some related to school of management. After you are done write in the output/design.md what you changed and why it should help customers stick around and buy. make sure to keep it short and concrete.

## Problem 11: Site testing (app check)

What was lacking: didn't name which item or usability feature to show. I used the Champion Reverse Weave Hoodie 1 (two sold-out sizes, so a wrong answer would show), "what hoodies do you have?", and the Problem 9 size filter + price sort. Each check has the steps, a screenshot, what it proves, and the matching database values. Screenshots are in output/app_check_images/ with relative links.

### Prompts

#### Prompt 1

problem 11: Site testing (app check). Now lets test the live site and document it in output/app_check.html. This is a page you can double-click open. include the clear screenshots and captions for : chat checking the inventory level of an item. Make sure it is honest stock/price from the database. 2) the dynamic search result cards appearing after a category question (e.g. hoodies). 3) one of the usability features you added in Problem 9. Make sure that the HTML is easy to grade: i.e., checkheading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).

## Problem 12: Audit trail, safety, finish harness

What was lacking: didn't say whether the trail may hold chat text (output/ is public) or which safety risks matter most. Kept personal data out of the trail (tool names, short args and result summaries, stop reasons only), appended to a valid JSON array without rewriting earlier events, and added 12 grouped safety rules. Testing found the provider content filter blocked a self-harm message and returned a generic error; added a crisis handler that runs before the model (988 / Yale Mental Health, not saved) and polite content-filter handling. Finished harness.md with an overview (§0) and §10. Follow-up: added §11 Reference covering all 23 models in models.py with fields and reasons, the 6 tools and what the assistant can and can't do, safety rules across all layers, a specs table with values read from the code, and setup/run/test commands. Added code/backend/.env.example.

### Prompts

#### Prompt 1

Problem 12: Audit trail, safety, finish harness

#### Prompt 2

Keep an append-only output/audit_trail.json of agent loop activity (time tool name short args/result stop reason). do not wipe between runs. Also think of some safety rules to give the agent and put them in prompts/prompt.md

#### Prompt 3

finish output/harness.md so it knows how the system works. Model fiels in models.py and why you chose them. Tools and abilities. Safety rules. Specs (loop limits, result caps, models, how to run front + back).

## Problem 13: Push to GitHub and submit the URL

What was lacking: the GitHub CLI is not installed, so the repo has to be created on github.com and pushed with git; repo name and commit email had to be chosen. Restructured to the required layout (frontend/, backend/, output/, root requirements.txt, .env.example with placeholders, .gitignore, README.md); the data pack (data/campus_customs.db + data/products/) stays local and gitignored; README explains the data pack, the four agent files, and running back + front. Secret scan of tracked files: no key or passwords; removed a real professor email from harness test notes. Backend now starts without the data pack and health lists what is missing.

### Prompts

#### Prompt 1

Problem 13: Push to GitHub and submit the URL

#### Prompt 2

do not use real .env, campust_customs.db, or product images in the GitHub repo. use .gitignore.  include .env.example with placeholders only. The expected file layout is: as seen in the picture

(The attached picture showed this layout:)

```
hw4/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── frontend/            # Vite React TypeScript app
├── backend/
│   ├── main.py          # FastAPI app — run with: uvicorn main:app
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   └── prompts/
│       └── prompt.md
└── output/
    ├── harness.md
    ├── design.md
    ├── usability.md
    ├── app_check.html
    ├── app_check_images/   # screenshots linked from app_check.html
    └── audit_trail.json
```

#### Prompt 3

(Answers chosen in the setup questions:) Create the repo myself on github.com · repo name: hw4 · commit email: GitHub no-reply email

#### Prompt 4

there is a local-only data pack (not in git): . Also note that the agent itself is four files under backend/: prompts/prompt.md, agent.py, tools.py, and models.py. README.md should explain how to run the front end and back end after placing the data pack.

(The attached picture showed the data pack layout:)

```
data/
├── campus_customs.db
└── products/            # images referenced by the catalogue
```

#### Prompt 5

https://github.com/shritanjay/hw4

#### Prompt 6

where to run in which terminal?

#### Prompt 7

it keeps failing

#### Prompt 8

but my user name is shritanjay.bhatia@yale.edu

#### Prompt 9

(ran in the chat's shell:) git push -u origin main  →  fatal: not a git repository (or any of the parent directories): .git

#### Prompt 10

still doesnt work

#### Prompt 11

i have done option a can you checl
