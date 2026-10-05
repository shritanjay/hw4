# Usability improvements (Problem 9)

Four improvements to the Campus Customs shop: two on the website, two in the shop assistant (agent) behind it. Each one started from a problem we actually hit while testing the earlier problems. Technical detail and test results are in `harness.md` §8.

> Note on timing: the improvements were built first, then this file was written from the build notes and test results. The "Problem we saw" lines record what prompted each change.

---

## 1. Shop by size, sort, and see stock on every card

**Problem we saw:** the Products page had 102 items and only a search box and category buttons. A shopper who wears a medium had to open items one by one to find out whether M was available, and there was no way to put the cheapest items first.

**What we added**
- **"My size" buttons (XS–XXL)** that show only items in stock in that size, each marked with a green "M in stock" badge.
- An **"In stock only"** checkbox.
- **Sort:** Featured, Price low → high, Price high → low, Name A–Z.
- **Sizes on every card** ("Sizes: S · M · L · XXL"), or "Only XS, L left" in amber when two or fewer sizes remain.
- A **Reset filters** link, a friendly "No products match in size XS" message with a one-click clear, and loading placeholders instead of a blank page.
- Filters are kept in the web address, so Back works and a link like "hoodies in M, cheapest first" can be shared.

**Why it helps the shopper**
- Size is usually the first question when buying clothes. Picking "M" once turns 102 items into the ~80 they can actually buy, with no dead ends.
- Students on a budget can sort by price and see that tees start at $32.
- Seeing sizes on the card, and "only 2 sizes left", answers "is it available?" before they click, and gives a gentle nudge to act on low-stock items.

**Why it helps the business**
- Fewer shoppers leave after clicking into items they can't buy.
- Fewer "do you have this in M?" questions to the chat or by phone/email (orderdept@campuscustoms.com).
- Shareable filtered links ("all Yale Mom items") are easy to post for Family Weekend or Harvard–Yale.

---

## 2. A chat that fits the page you're on

**Problem we saw:** the chat offered the same three suggestions everywhere, and they disappeared after the first message. Waiting for an answer showed a static "…". On a phone the floating chat window covered the page and was hard to use.

**What we added**
- **Quick-reply buttons that change with the page:**
  - on an item's page: "Is this in M?", "What sizes are left?", "Do you have this in another color?"
  - when chat results are showing: "Which of these is cheapest?", "Any of these in XL?"
  - elsewhere: "What t-shirts do you have?", "Gift for a Yale mom", "Navy hoodies under $70"
- An **animated "typing" indicator** while the assistant thinks.
- Opening the chat puts the cursor in the message box, and **Esc** closes it.
- On **phones the chat opens full-screen**, with text large enough that iPhones don't zoom in.
- If a shopper pastes a card number or password, they see a **🔒 notice** that it was removed (see #4).

**Why it helps the shopper**
- On a hoodie's page the most likely questions are one tap away. They don't have to type, and they don't even need to name the item ("this" works).
- Many visitors (students between classes, parents on the go) browse on phones. A full-screen chat is readable and easy to type in.
- The typing indicator makes it clear the assistant is working, so shoppers don't resend or give up.

**Why it helps the business**
- More shoppers actually use the assistant, and each conversation starts from a buying question (size, color, stock).
- A good mobile experience matters for a campus shop whose customers are mostly on their phones.

---

## 3. A faster, cheaper assistant

**Problem we saw:** we started logging each chat turn (time, how much text was sent to the AI, which tools it used). A simple question like "Is the Yale Grandpa Crewneck in M?" took three trips to the AI model, and every trip resent a long 12 KB instruction sheet. The AI was also looking up account details for a guest asking about returns.

**What we added**
- **A cost and speed log** for every chat turn (time, size, tools used; no message text), plus a 6-question benchmark so changes can be measured, not guessed.
- **Look up an item by name in one step.** The stock and product-info tools now accept a name like "Yale Grandpa Crewneck" directly, instead of needing a search first. If a name is ambiguous ("grandpa" = hoodie or crewneck), it asks which one instead of guessing.
- **A shorter instruction sheet:** half the size, same rules.
- **Only offer the AI the tools that make sense right now:** account tools only for logged-in shoppers, and "this product" only on a product page.

**Results on the same 6 questions:** text sent to the AI **down 45%** (69,731 → 38,162 tokens), AI calls 16 → 14, typical answer time 4.1 s → 3.5 s. Named-item stock questions went from 3 AI trips to 2.

**Why it helps the shopper**
- Faster answers to the most common question ("is it in my size?").
- Clearer behavior: if they're vague, the assistant asks which item they mean instead of answering about the wrong one.

**Why it helps the business**
- The AI bill scales with the text sent, so a 45% cut makes each conversation almost half the cost. That matters on game weekends and move-in, when chat volume spikes.
- The log shows exactly where time and money go, so future changes can be checked with numbers.

---

## 4. A more accurate, safer assistant

**Problems we saw:**
- Shoppers sometimes type card numbers ("just order it, my card is…"). The assistant told them not to, but the number had already been **sent to the AI provider and saved in the chat history** for logged-in shoppers.
- Asked "do you have this in pink?", the assistant said "no pink", but the **Big Yale Tri Blend T Shirt is dusty coral**, which most people would call pink. The catalogue just doesn't use the word.
- Nothing in the code stopped a reply from calling a sold-out size "available" if the AI slipped up.

**What we added**
- **Automatic removal of sensitive data** before the message reaches the AI or the database: card numbers (checked with the standard card-number checksum, so prices and order numbers aren't touched), Social Security numbers, card security codes, and "my password is …". The shopper sees their message with `[redacted card number]` and a 🔒 note that it wasn't saved or sent.
- **Color families in search:** "pink" also finds coral, rose, and salmon; "grey" finds charcoal and heather; "blue" finds navy and royal; and so on. When nothing is literally the requested color, the assistant says so honestly and offers the closest shade.
- **A sold-out check:** if a reply calls a size available when the stock lookup says it's sold out, the reply is rejected and the assistant must fix it before the shopper sees it. This sits alongside the earlier check that every price and quantity must come from the database.

**Why it helps the shopper**
- Their card numbers and passwords aren't stored in a chat log or sent to a third-party AI, even if they paste one by mistake.
- They find what they're actually looking for ("pink" → the dusty coral tee at $32) instead of a dead end, with an honest "closest shade" explanation.
- They can trust "in stock" answers, so they don't plan a trip to 57 Broadway for a size that's gone.

**Why it helps the business**
- **Less risk:** not storing card numbers or SSNs keeps sensitive data out of the shop's database and its AI provider's logs.
- **More sales from the same catalogue:** color-family matching surfaces items the old search hid.
- **Fewer complaints and returns** from wrong stock answers, and more trust in the assistant.
