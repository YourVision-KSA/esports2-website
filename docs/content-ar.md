# Arabic Content — Single Source of Truth

Source for KEEP strings: `reference/prototype.html` (the **content reference**). Every
user-facing string in templates comes from this file, **copied exactly**. Status values:

- **KEEP** — exact text from `reference/prototype.html`, reuse verbatim (character for character).
- **REPLACE** — prototype text that encodes the old format (4 tournaments / 1 day / 32 seats /
  teams); owner must supply new copy. The old text is kept for reference only — do not ship it.
- **APPROVED** — supplied or approved by the owner; ship as-is.
- **DRAFT** — proposed by the AI assistant; **needs owner review before shipping**.
- **TODO** — needed, no text yet.

AI assistants: never invent or alter Arabic silently. Add new rows as DRAFT and flag them.

## Site name, brand, footer

| Key | Text | Status |
|---|---|---|
| SITE-NAME | يوم الرياضات الإلكترونية | KEEP (pending DEC-02) |
| BRAND | يوم الرياضات الإلكترونية | KEEP — prototype renders it as «يوم» + emphasized «الرياضات الإلكترونية» |
| FOOTER-1 | يوم الرياضات الإلكترونية · الرياض | KEEP |
| FOOTER-2 | الرعاة والشركاء: تضاف الشعارات هنا | KEEP (placeholder until sponsor logos exist) |

## Navigation

| Key | Text | Status |
|---|---|---|
| NAV | البطولات · المناطق · الجدول · الجوائز · الأسئلة · التسجيل | KEEP |
| NAV-VOTE | التصويت | DRAFT (add during vote phase) |

## Hero

| Key | Text | Status |
|---|---|---|
| HERO-TITLE | يوم الرياضات الإلكترونية | KEEP (glitch effect splits it: «يوم» + «الرياضات الإلكترونية») |
| HERO-TEXT | يوم كامل من البطولات، اللعب الحر، وتجارب الواقع الافتراضي. تعال بفريقك أو لوحدك، ونافس على المسرح الرئيسي أمام الجمهور. | REPLACE — "one full day" and "with your team"; event is 3 days, 1v1 only |
| HERO-BTN-1 | سجّل الآن | KEEP (registration phase; vote phase uses HERO-BTN-VOTE) |
| HERO-BTN-VOTE | صوّت الآن | DRAFT |
| HERO-BTN-2 | جدول اليوم | REPLACE — one-day wording (suggest: جدول الفعالية — DRAFT) |
| HERO-STAT-1 | 4 / بطولات رئيسية | REPLACE — new: 3 / بطولات (DRAFT) |
| HERO-STAT-2 | 6 / مناطق تجربة | KEEP (zones unchanged) |
| HERO-STAT-3 | 10 / ساعات متواصلة | REPLACE — new: 3 / أيام (DRAFT) |
| HERO-3D-HINT | اسحب يد التحكم لتدويرها | KEEP (depends on final 3D scene subject — DEC-15) |
| HERO-3D-ARIA | مجسم ثلاثي الأبعاد ليد تحكم على منصة مضيئة وحولها سماعة ومفاتيح وجواهر عائمة | KEEP (depends on final 3D scene — DEC-15) |
| HUD labels | PRESS START ▶ · P1 READY | KEEP (English; new design may restyle) |

## Section headings and eyebrow labels

| Key | Text | Status |
|---|---|---|
| SEC-GAMES | البطولات | KEEP |
| SEC-GAMES-LEAD | أربع بطولات بنظام خروج المغلوب، والنهائيات كلها على المسرح الرئيسي. | REPLACE — "four"; new: ثلاث بطولات بنظام خروج المغلوب، والنهائيات كلها على المسرح الرئيسي. (DRAFT) |
| SEC-ZONES | مناطق الفعالية | KEEP |
| SEC-SCHEDULE | جدول اليوم | REPLACE — one-day wording (suggest: جدول الفعالية — DRAFT) |
| SEC-PRIZES | الجوائز | KEEP |
| SEC-RULES | قواعد المشاركة | KEEP |
| SEC-FAQ | أسئلة متكررة | KEEP |
| SEC-JOIN | احجز مقعدك في البطولة | KEEP |
| Eyebrows | SELECT TOURNAMENT · WORLD MAP · STAGES · LOOT · RULES · HELP · JOIN GAME | KEEP (English; new design may restyle) |

## Tournaments section

Prototype cards (REPLACE — old format, reference only):

| Game | Tag | Description | Facts |
|---|---|---|---|
| كرة القدم | FOOTBALL · 1v1 | مواجهات فردية سريعة، كل مباراة شوطين. | المقاعد: 32 · المنصة: PS5 |
| القتال | FIGHTING · 1v1 | أفضل من ثلاث جولات، والنهائي أفضل من خمس. | المقاعد: 32 · المنصة: PS5 |
| التصويب الجماعي | SHOOTER · 5v5 | فرق من خمسة لاعبين، والتواصل بينهم يحسم النتيجة. | الفرق: 8 · المنصة: PC |
| سباق السيارات | RACING · SIM | أسرع لفة على مقاعد المحاكاة تتأهل للنهائي. | المقاعد: مفتوحة · المنصة: SIM RIG |

Reusable card labels (KEEP): المقاعد · المنصة

New cards (game names come from the DB; display names DRAFT, pending vote + owner wording):

| Key | Text | Status |
|---|---|---|
| GAME-RL | روكيت ليج — ROCKET LEAGUE — 1v1 — 16 لاعبًا | DRAFT |
| GAME-FIFA | فيفا — EA SPORTS FC — 1v1 — 16 لاعبًا | DRAFT |
| GAME-COD | كول أوف ديوتي — CALL OF DUTY — 1v1 — 16 لاعبًا | DRAFT |
| SEATS-LEFT | المقاعد المتبقية: {n} | DRAFT |
| SEATS-FULL | اكتملت المقاعد — يمكنك الانضمام إلى قائمة الانتظار | DRAFT |

## Zones (all KEEP — exact prototype text)

| Zone | Description |
|---|---|
| المسرح الرئيسي | شاشة عرض كبيرة، معلّق مباشر، ومدرجات للجمهور. |
| ساحة البطولات | محطات لعب مجهزة للأدوار التمهيدية مع حكّام. |
| اللعب الحر | أجهزة مفتوحة للجميع طوال اليوم بدون تسجيل. |
| الواقع الافتراضي | تجارب VR قصيرة بالدور، مع مشرف لكل محطة. |
| ركن الريترو | ألعاب كلاسيكية وأجهزة أركيد لمن يحب القديم. |
| معرض المجسمات | مجسمات مطبوعة بتقنية ثلاثية الأبعاد وركن للتصوير. |

Note for owner: «طوال اليوم» in اللعب الحر is one-day wording — review for the 3-day event.

## Schedule

Prototype single-day schedule (REPLACE as a set — event is 3 days; keep as tone reference):

| Time | Item | Description |
|---|---|---|
| 12:00 | فتح الأبواب وتأكيد الحضور | استلام البطاقات وتوزيع اللاعبين على المحطات. |
| 13:00 | الافتتاح | كلمة ترحيب وعرض افتتاحي على المسرح. |
| 13:30 | الأدوار التمهيدية | تنطلق البطولات الأربع بالتوازي في ساحة البطولات. |
| 16:30 | استراحة ومسابقات الجمهور | تحديات سريعة وسحوبات على جوائز فورية. |
| 17:30 | نصف النهائي | تنتقل المباريات إلى المسرح الرئيسي مع تعليق مباشر. |
| 20:00 | النهائيات | نهائي كل بطولة واحدًا تلو الآخر. |
| 21:30 | التتويج والختام | تسليم الكؤوس والجوائز وصورة جماعية. |

| Key | Text | Status |
|---|---|---|
| SCHEDULE-NOTE | الجدول مقترح، والتاريخ والمكان يُعلنان عند اعتمادهما. | KEEP |
| SCHEDULE-3DAY | — | TODO (owner; depends on DEC-01 + permits) |

## Prizes (KEEP — exact prototype text; values TODO per DEC-13)

| Place | Text |
|---|---|
| المركز الأول | كأس البطولة، ميدالية ذهبية، والجائزة الكبرى. |
| المركز الثاني | ميدالية فضية وجائزة قيّمة. |
| المركز الثالث | ميدالية برونزية وجائزة. |
| أفضل لاعب في اليوم | يختاره الحكّام من كل البطولات. |

| Key | Text | Status |
|---|---|---|
| PRIZES-3D-ARIA | مجسم ثلاثي الأبعاد لكأس ذهبي يدور تحت أضواء المسرح | KEEP (depends on final 3D scene — DEC-15) |
| HUD-WINNER | WINNER | KEEP (English) |

Note for owner: «أفضل لاعب في اليوم» may need rewording for a 3-day event.

## Rules

| Text | Status |
|---|---|
| الحضور قبل موعد مباراتك بربع ساعة، والتأخر يعني خسارة المباراة. | KEEP |
| قرار الحكم نهائي في كل الخلافات. | KEEP |
| يُسمح بإحضار يد التحكم أو السماعة الخاصة بك. | KEEP |
| الروح الرياضية شرط، وأي إساءة تعني الاستبعاد. | KEEP |
| يمنع استخدام أي برامج أو أدوات غش. | KEEP |
| لكل لاعب بطولتان كحد أقصى حتى لا تتعارض المواعيد. | **REPLACE** — rule is now ONE: يمكن لكل لاعب التسجيل في بطولة واحدة فقط لإتاحة الفرصة لأكبر عدد من اللاعبين. (DRAFT) |

## FAQ (exact prototype text)

| Question | Answer | Status |
|---|---|---|
| هل أقدر أحضر كمتفرج فقط؟ | نعم. منطقة اللعب الحر والواقع الافتراضي وركن الريترو مفتوحة للجميع، والمدرجات متاحة لمتابعة النهائيات. | KEEP |
| ما عندي فريق، كيف أشارك في البطولة الجماعية؟ | سجّل كلاعب فردي واختر البطولة الجماعية، ونجمعك مع لاعبين آخرين قبل الفعالية. | REPLACE — no team tournament (all 1v1); suggest removing this entry |
| هل الأجهزة متوفرة؟ | كل الأجهزة والشاشات متوفرة في الموقع. أحضر ملحقاتك الخاصة فقط لو تفضّلها. | KEEP |
| متى يغلق التسجيل؟ | يغلق عند اكتمال المقاعد في كل بطولة، فالأولوية للأسبق. | KEEP |

## Join section

| Key | Text | Status |
|---|---|---|
| JOIN-TITLE | احجز مقعدك في البطولة | KEEP |
| JOIN-TEXT | المقاعد محدودة لكل بطولة. جهّز اسمك، اسم اللاعب (Gamer Tag)، والبطولة التي تريدها. | KEEP |
| JOIN-BTN | رابط التسجيل يضاف هنا | REPLACE — prototype placeholder; real CTA is HERO-BTN-1 (سجّل الآن) linking to /register/ |

## Vote flow (all DRAFT — owner review required; counting-rules text also DEC-03)

| Key | Text |
|---|---|
| VOTE-TITLE | صوّت لاختيار ألعاب البطولة |
| VOTE-INSTR | اختر {n} ألعاب من القائمة. صوت واحد لكل متصفح. |
| VOTE-SUBMIT | إرسال الصوت |
| VOTE-DONE | تم تسجيل صوتك، شكرًا لمشاركتك! |
| VOTE-HELD-SAME-PAGE | (held ballots see VOTE-DONE — no separate message) |
| VOTE-DUP | لقد شاركت في التصويت مسبقًا. |
| VOTE-CLOSED | انتهى التصويت. تابعنا لمعرفة الألعاب المختارة! |
| VOTE-RULES | قواعد الاحتساب: صوت واحد لكل متصفح. تُراجع الأصوات المشبوهة آليًا وقد تُستبعد الأصوات الآلية أو المكررة. نتيجة التصويت استرشادية وتساعد المنظمين في اختيار الألعاب، وقرار المنظمين نهائي. |
| VOTE-RESULTS-TITLE | نتائج التصويت |
| VOTE-RESULTS-NOTE | الأصوات المحتسبة: {counted} · أصوات قيد المراجعة/مستبعدة: {held} |

## Registration flow (all DRAFT)

| Key | Text |
|---|---|
| REG-TITLE | التسجيل في البطولة |
| REG-CHOOSE | اختر بطولتك — يمكنك التسجيل في بطولة واحدة فقط |
| REG-FIELD-NAME | الاسم الكامل |
| REG-FIELD-PHONE | رقم الجوال |
| REG-FIELD-EMAIL | البريد الإلكتروني (اختياري — نرسل إليه رابط إدارة التسجيل) |
| REG-FIELD-GAMERTAG | {game_player_id_label} |
| REG-CONSENT | أوافق على سياسة الخصوصية ومعالجة بياناتي لأغراض تنظيم الفعالية |
| REG-SUBMIT | تأكيد التسجيل |
| REG-OK-CONFIRMED | تم تأكيد تسجيلك في {game}! |
| REG-OK-WAITLIST | اكتملت المقاعد — تمت إضافتك إلى قائمة الانتظار (ترتيبك: {n}) |
| REG-SAVE-LINK | احفظ هذا الرابط لإدارة تسجيلك: |
| REG-LINK-EMAILED | أرسلنا رابط إدارة التسجيل إلى بريدك الإلكتروني أيضًا. |
| REG-DUP-TOURNAMENT | لديك تسجيل قائم بالفعل — يمكن لكل لاعب التسجيل في بطولة واحدة فقط |
| REG-FULL | اكتملت المقاعد وقائمة الانتظار لهذه البطولة |
| REG-CLOSED | التسجيل مغلق حاليًا |
| REG-WITHDRAW | الانسحاب من البطولة |
| REG-WITHDRAW-CONFIRM | هل أنت متأكد؟ سيُعطى مقعدك لأول لاعب في قائمة الانتظار. |
| REG-WITHDRAWN | تم الانسحاب. نراك في مناطق اللعب الحر! |

## Email: manage link (all DRAFT)

| Key | Text |
|---|---|
| EMAIL-MANAGE-SUBJECT | رابط إدارة تسجيلك — {site_name} |
| EMAIL-MANAGE-BODY | أهلًا {name}، تم استلام تسجيلك في بطولة {game}. حالة التسجيل: {status}. لإدارة تسجيلك أو الانسحاب، استخدم هذا الرابط الخاص بك ولا تشاركه مع أحد: {manage_url} |

## Bracket / results (all DRAFT)

| Key | Text |
|---|---|
| BRACKET-TITLE | جدول المباريات والنتائج |
| ROUND-1 | دور الـ16 |
| ROUND-2 | ربع النهائي |
| ROUND-3 | نصف النهائي |
| ROUND-4 | النهائي |
| MATCH-PENDING | لم تُلعب بعد |
| MATCH-FORFEIT | انسحاب |
| CHAMPION | البطل |

## Invitations / check-in

| Key | Text | Status |
|---|---|---|
| INVITE-TITLE | دعوة خاصة — تجمع الرياضات الإلكترونية | DRAFT |
| INVITE-BODY | يسعدنا دعوتكم لحضور الفعالية. يُرجى إبراز رمز الدعوة عند البوابة. | DRAFT |
| CHECKIN-OK | تم تأكيد الحضور — أهلًا وسهلًا | APPROVED (owner, 2026-10) |
| CHECKIN-ALREADY | هذه الدعوة مستخدمة مسبقًا ({time}) | DRAFT |
| CHECKIN-INVALID | دعوة غير صالحة | DRAFT |

## Strings added during the build (all DRAFT — flagged for owner review 2026-10-20)

| Key | Text | Where used |
|---|---|---|
| HERO-TEXT (new draft) | ثلاثة أيام من المنافسات الفردية على ثلاث بطولات، مع مناطق لعب حر وتجارب واقع افتراضي. نافس على المسرح الرئيسي أمام الجمهور. | hero paragraph (replaces the 1-day/teams text) |
| HERO-BTN-SCHEDULE / SEC-SCHEDULE | جدول الفعالية | hero button + schedule heading |
| SEC-GAMES-LEAD (new draft) | ثلاث بطولات بنظام خروج المغلوب، والنهائيات كلها على المسرح الرئيسي. | games section lead ("three" instead of "four") |
| HERO-STATS (new draft) | 3 بطولات · 6 مناطق تجربة · 3 أيام | hero stats (middle one is KEEP) |
| SCHEDULE-TBA | يُعلن جدول الأيام الثلاثة قريبًا. | schedule placeholder until DEC-01 |
| RULE-ONE-TOURNAMENT | يمكن لكل لاعب التسجيل في بطولة واحدة فقط لإتاحة الفرصة لأكبر عدد من اللاعبين. | rules list (replaces the two-tournament rule) |
| REG-LINK-EXISTING | استخدم رابط الإدارة الذي حصلت عليه سابقًا، أو تواصل مع المنظمين إذا فقدته. | re-registration success page |
| STAFF-RESULTS-TITLE | إدخال النتائج | referee results page |
| STAFF-CHECKIN-TITLE | تسجيل الحضور | door-staff page |
| STAFF-SEARCH | بحث | door-staff guest search |
| Seed game names | روكيت ليج · فيفا · كول أوف ديوتي · تيكن · فالورانت | candidate games (data; editable in admin) |
| GAMES-PENDING-VOTE | الألعاب النهائية تُعتمد بعد انتهاء التصويت العام. | note under the tournaments grid |
| COUNTDOWN-LABEL | ينطلق الحدث بعد | hero countdown (design rev 2) |
| COUNTDOWN-TBA | يُعلن التاريخ قريبًا | hero countdown, until DEC-01 |
| COUNTDOWN-UNITS | يوم · ساعة · دقيقة · ثانية | countdown cells |
| STAT-CAPTIONS | بطولات رئيسية · لاعبًا متنافسًا · مناطق تجربة · أيام متواصلة | big-stats band (3 / 48 / 6 / 3) |
| PATH-PLAYERS | للاعبين — نافس في البطولات | dual-path section title (body reuses JOIN-TEXT) |
| PATH-FANS | للجمهور — عيش الأجواء | dual-path section title (body reuses the KEEP FAQ spectator answer) |
| TIER-DIAMOND / GOLD / SILVER | الراعي الماسي · الراعي الذهبي · الراعي الفضي · شريك مشارك | tiered sponsor rows (tiers are FACT from the brief) |

## System / errors (all DRAFT)

| Key | Text |
|---|---|
| ERR-RETRY | حدث خطأ مؤقت — يُرجى المحاولة مرة أخرى |
| ERR-404 | الصفحة غير موجودة |
| PHASE-SOON | قريبًا — تابعونا |

## Still TODO (owner)

Event date + venue text · 3-day schedule · prize values · privacy notice (DEC-08) · guardian
consent text if minors allowed (DEC-09) · sponsor names/logos · stream link labels ·
new hero paragraph (HERO-TEXT replacement) · final game display names after the vote ·
review of «طوال اليوم» and «أفضل لاعب في اليوم» wording for a 3-day event.
