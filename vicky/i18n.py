"""Français: Canada has two official languages, so Vicky speaks both.

tr(text, lang, **kw) returns the French version of an on-screen English string (or the English one if no
translation exists), then fills any {placeholders}. Numbers are never translated here: they come from the
engine, in the same format the audit checks. AI replies are asked for in Canadian French via ai_instruction().
"""

LANGS = {"en": "English", "fr": "Français"}

FR = {
    # header, navigation, footer
    "Vicky · Seed readiness": "Vicky · Préparation à l’amorçage",
    "Connected books: Oct 2024 to Sep 2026": "Livres connectés : oct. 2024 à sept. 2026",
    "Start here": "Commencer ici",
    "Practise": "S’exercer",
    "Investor Q&A": "Questions d’investisseurs",
    "Partner meeting": "Réunion des associés",
    "Offer round": "Tour des offres",
    'Getting ready': 'En préparation',
    'Almost there': 'Presque prêt',
    'Ready for the partner meeting': 'Prêt pour la réunion des associés',
    'Your business is strong: {n} things investors will like': 'Votre entreprise est solide : {n} atouts qui plairont aux investisseurs',
    'Your deck: {n} claims to fix': 'Votre présentation : {n} affirmations à corriger',
    'Your answers: {n} of your top 3 practised': 'Vos réponses : {n} de vos 3 questions clés pratiquées',
    "<b>That's an answer a lead investor writes down.</b> {w} out of 5. That's {n} of your top 3 done.": '<b>C’est une réponse qu’un investisseur principal prend en note.</b> {w} sur 5. Ça fait {n} de vos 3 questions clés de réglées.',
    'Your fix path': 'Votre parcours de corrections',
    'Each fix unlocks the next. Practise one and watch the next domino fall.': 'Chaque correction débloque la suivante. Pratiquez-en une et regardez le prochain domino tomber.',
    'Step': 'Étape',
    'of': 'sur',
    'Fixed': 'Corrigé',
    'Up next': 'À venir',
    'First fix': 'Première correction',
    'Latest fix': 'Dernière correction',
    'Survive the raise': 'Traverser la levée de fonds',
    'Hold spending until a term sheet is signed': 'Geler les dépenses jusqu’à la signature d’une lettre d’intention',
    'Now you have time to fix the story': 'Vous avez maintenant le temps de corriger le discours',
    'Fix the deck numbers': 'Corriger les chiffres de la présentation',
    'Quote real ARR, churn and margin': 'Citer les vrais RRA, taux d’attrition et marge',
    'Now investors trust your numbers': 'Les investisseurs font maintenant confiance à vos chiffres',
    'Explain the growth slowdown': 'Expliquer le ralentissement de la croissance',
    'Show the evidence from customers': 'Montrer les preuves venant des clients',
    'Now the $5M plan is believable': 'Le plan de 5 M$ devient crédible',
    'Make the forecast honest': 'Rendre les prévisions honnêtes',
    'Cash from collections, no unfiled SR&ED, realistic pricing': 'Trésorerie selon les encaissements, aucun RS&DE non déposé, hausse de prix réaliste',
    'Now the plan survives diligence': 'Le plan résiste maintenant à la vérification diligente',
    'Pitch the whole partnership': 'Présenter à tous les associés',
    'Not yet': 'Pas encore',
    'Practised to 4+/5': 'Pratiqué à 4/5 ou plus',
    'Practise it to 4+/5': 'À pratiquer jusqu’à 4/5',
    "The last step of a raise: the offers. Tell the investors what you're asking for and each one makes an offer. You have <b>{secs} seconds</b> to accept one, counter, or walk away. Then you'll see how they respond, and what the deal really means.": 'La dernière étape d’une levée de fonds : les offres. Dites aux investisseurs ce que vous demandez, et chacun vous fait une offre. Vous avez <b>{secs} secondes</b> pour en accepter une, faire une contre-offre ou tout refuser. Ensuite, vous verrez comment ils réagissent et ce que l’entente signifie vraiment.',
    'How the offer round works': 'Comment fonctionne le tour des offres',
    "Numbers come from code. The AI writes the investors' words and Vicky's explanation, and an independent check reviews every figure before you see it.": 'Les chiffres viennent du code. L’IA rédige les propos des investisseurs et l’explication de Vicky, et une vérification indépendante contrôle chaque chiffre avant que vous le voyiez.',
    "**You set the ask.** How much you're raising, and for how much of the company. Vicky never suggests a valuation: the number is yours.": '**Vous fixez votre demande.** Combien vous levez, et pour quelle part de l’entreprise. Vicky ne suggère jamais de valorisation : le chiffre vous appartient.',
    "**The investors make offers.** Each one at the table makes one offer in their own style: less money, more equity, or a condition like a board seat. Offers stay within each investor's real cheque size (Appendix E) and a realistic range set by your SAFE caps.": '**Les investisseurs font leurs offres.** Chacun fait une offre à sa manière : moins d’argent, plus de participation, ou une condition comme un siège au conseil. Les offres restent dans la taille de chèque réelle de chaque investisseur (annexe E) et dans une fourchette réaliste fixée par vos plafonds de SAFE.',
    '**You decide on the clock.** Each offer card shows what it really means: the valuation before and after the money, how it compares with your ask, and how much of the $4M it covers. Accept, counter or walk away within {secs} seconds.': '**Vous décidez contre la montre.** Chaque offre montre ce qu’elle signifie vraiment : la valorisation avant et après l’investissement, l’écart avec votre demande et la part des 4 M$ qu’elle couvre. Acceptez, faites une contre-offre ou refusez en {secs} secondes.',
    '**The investors respond.** Counter too far and an investor holds firm or walks away; stay close and they accept or meet you halfway. If the lead fund signs, the government-backed fund joins at the same price.': '**Les investisseurs réagissent.** Une contre-offre trop éloignée et l’investisseur maintient son offre ou se retire; restez proche et il accepte ou coupe la poire en deux. Si le fonds principal signe, le fonds gouvernemental se joint au même prix.',
    '**Vicky explains the deal.** Money agreed versus still on the table, the ownership you give up, the conditions you accept, and how your SAFEs convert. She never says which offer to take.': '**Vicky vous explique l’entente.** L’argent convenu par rapport à celui encore sur la table, la part que vous cédez, les conditions acceptées et la conversion de vos SAFE. Elle ne dit jamais quelle offre accepter.',
    "Ask Vicky": "Demander à Vicky",
    "Financials": "Données financières",
    "Vicky's Partner Meeting": "La réunion des associés de Vicky",
    "Numbers come from your books, not the AI. Vicky gives no investment or valuation advice.":
        "Les chiffres viennent de vos livres, pas de l’IA. Vicky ne donne aucun conseil d’investissement ni d’évaluation.",
    # sidebar
    "Your AI finance team": "Votre équipe financière IA",
    "AI Finance Officer (CFO) · forecasts": "Directeur financier IA · prévisions",
    "AI Risk Officer (CRO) · monthly checks": "Directeur des risques IA · contrôles mensuels",
    "Coming from June": "Bientôt chez June",
    "AI VC · seed meeting prep": "IA en capital de risque · préparation des rencontres",
    "Readiness": "Préparation",
    "{ready} of {total} roadblocks you can answer well": "{ready} obstacles sur {total} que vous maîtrisez",
    "🧠 Learn the lingo": "🧠 Apprendre le jargon",
    "♿ Accessibility": "♿ Accessibilité",
    "⚙️ AI settings": "⚙️ Réglages de l’IA",
    "Français (French)": "Français (French)",
    "Larger text": "Texte plus grand",
    "High contrast": "Contraste élevé",
    "Reduce motion": "Réduire les animations",
    "Books synced 30 Sep 2026 · CAD": "Livres synchronisés le 30 sept. 2026 · CAD",
    "Fictional company, synthetic data": "Entreprise fictive, données synthétiques",
    "📖 Take the free 10-Minute Test": "📖 Faire le test gratuit de 10 minutes",
    # Start here
    "View breakdown →": "Voir le détail →",
    "Open with sources →": "Ouvrir avec les sources →",
    "Practise →": "S’exercer →",
    "Practise this →": "S’exercer →",
    "Practise this now →": "S’exercer maintenant →",
    "Snapshot": "Aperçu",
    "Source key:": "Légende des sources :",
    "Not seed-ready yet. Practising your top 3 moves you to {n}.":
        "Pas encore prêt pour l’amorçage. Pratiquer vos 3 questions principales vous amène à {n}.",
    "Getting there. Next up: {next}.": "Vous progressez. Prochaine étape : {next}.",
    "Every roadblock answered well. The last points come from fixing the deck itself.":
        "Tous les obstacles sont maîtrisés. Les derniers points viennent de la correction de la présentation.",
    "“Your growth is real and your burn is efficient. Lead with that. But fix three things before your first meeting, and one of them isn't in your deck.”":
        "« Votre croissance est réelle et votre consommation de trésorerie est efficace. Commencez par ça. Mais corrigez trois choses avant votre première rencontre, et l’une d’elles n’est pas dans votre présentation. »",
    "“Good progress. Next, get ready for this: {next}.”": "« Beau progrès. Ensuite, préparez-vous à ceci : {next}. »",
    "“You can answer everything they'll ask. Time for my partner meeting.”":
        "« Vous pouvez répondre à tout ce qu’on vous demandera. Place à ma réunion des associés. »",
    "Vicky, from a review of 24 months of your books and 9 deck claims":
        "Vicky, après l’examen de 24 mois de vos livres et de 9 affirmations de votre présentation",
    "Practise roadblock {rank}: {title} →": "Pratiquer l’obstacle {rank} : {title} →",
    "Enter {panel} →": "Entrer dans {panel} →",
    "Your path to a Series A": "Votre parcours vers une série A",
    "Where you are, what's in the way, and where you want to be.": "Où vous en êtes, ce qui bloque, et où vous voulez aller.",
    "Where you are · Sep 2026": "Où vous en êtes · sept. 2026",
    "What's in the way": "Ce qui bloque",
    "Where you want to be": "Où vous voulez aller",
    "Your plan gets there in": "Votre plan y arrive en",
    "At the growth you've actually had, cash runs out in": "Au rythme de croissance réel, la trésorerie s’épuise en",
    "before you get there": "avant d’y arriver",
    "👤 = bring in a human: a June CPA and a startup lawyer.": "👤 = faire appel à une personne : un CPA de June et un avocat en démarrage d’entreprise.",
    "Top 3 questions you'll be asked": "Les 3 questions qu’on vous posera",
    "Prepare crisp, sourced answers before the first call.": "Préparez des réponses claires et sourcées avant le premier appel.",
    "Strengths": "Forces",
    "{n} signals investors will like.": "{n} signaux que les investisseurs apprécieront.",
    "Weaknesses": "Faiblesses",
    "{n} areas likely to draw scrutiny.": "{n} points qui attireront l’attention.",
    "Next actions": "Prochaines actions",
    "Do these before you send the deck.": "À faire avant d’envoyer la présentation.",
    "Deck check: {n} of {total} claims need fixing": "Vérification : {n} affirmations sur {total} à corriger",
    "Every claim tested against your books. No AI involved.": "Chaque affirmation vérifiée dans vos livres. Aucune IA.",
    "{n} more things investors may raise": "{n} autres points que les investisseurs pourraient soulever",
    "BLIND SPOT": "ANGLE MORT",
    "Recurring revenue, per year": "Revenus récurrents, par an",
    "Monthly growth, last 3 months": "Croissance mensuelle, 3 derniers mois",
    "Months of cash left": "Mois de trésorerie restants",
    # journey: roadblocks, stages, cards
    "You could run out of cash before the round closes": "Vous pourriez manquer de trésorerie avant la clôture de la ronde",
    "Growth has nearly halved, and the $5M goal depends on it": "La croissance a presque diminué de moitié, et l’objectif de 5 M$ en dépend",
    "You're losing customers twice as fast as your deck says": "Vous perdez des clients deux fois plus vite que ne le dit votre présentation",
    "Your forecast counts revenue as cash": "Vos prévisions comptent les revenus comme de la trésorerie",
    "The plan counts on a $240K tax refund that isn't filed": "Le plan compte sur un remboursement d’impôt de 240 k$ non déposé",
    "The price increase hits customers you can't reprice yet": "La hausse de prix touche des clients que vous ne pouvez pas encore repositionner",
    "One customer is 10% of revenue, and their renewal isn't signed": "Un client représente 10 % des revenus, et son renouvellement n’est pas signé",
    "New salespeople won't close deals in their first month": "Les nouveaux vendeurs ne concluront pas de ventes dès le premier mois",
    "Know your numbers": "Connaître vos chiffres",
    "Fix your story": "Corriger votre récit",
    "Practise the questions": "Pratiquer les questions",
    "Build your investor list": "Dresser votre liste d’investisseurs",
    "First meetings": "Premières rencontres",
    "Diligence and partner meeting": "Vérification diligente et réunion des associés",
    "Term sheet and close": "Lettre d’intention et clôture",
    "Burn multiple (12 months)": "Multiple de consommation (12 mois)",
    "Annual recurring revenue": "Revenus récurrents annuels",
    "Churn after month 6 (monthly plans)": "Attrition après le 6e mois (forfaits mensuels)",
    "SR&ED refunds received": "Remboursements RS&DE reçus",
    "Largest customer's share of revenue": "Part des revenus du plus gros client",
    "Gross margin once support is counted": "Marge brute en incluant le soutien",
    "Revenue kept from last year's customers (NRR)": "Revenus conservés des clients de l’an dernier (NRR)",
    "Months of cash left at today's burn": "Mois de trésorerie au rythme actuel",
    "Hold spending at today's level until a term sheet is signed": "Maintenir les dépenses actuelles jusqu’à la signature d’une lettre d’intention",
    "Quote churn as 2.0% (12 months). Never 1%": "Citer une attrition de 2,0 % (12 mois). Jamais 1 %",
    "Explain the July–September slowdown with customer evidence": "Expliquer le ralentissement de juillet à septembre avec des preuves clients",
    "Rebuild the forecast's cash line from collections": "Reconstruire la ligne de trésorerie à partir des encaissements",
    "Show the plan without the $240K SR&ED refund": "Présenter le plan sans le remboursement RS&DE de 240 k$",
    "Replace the $2B TAM with a bottom-up build": "Remplacer le TAM de 2 G$ par une estimation ascendante",
    # questions shown by investors
    "What happens if the round takes longer than you expect?": "Que se passe-t-il si la ronde prend plus de temps que prévu?",
    "How fast are you growing?": "À quelle vitesse croissez-vous?",
    "What is your churn?": "Quel est votre taux d’attrition?",
    "What is your ARR, and how do you calculate it?": "Quels sont vos revenus récurrents annuels, et comment les calculez-vous?",
    "How fast do new account executives ramp, and how many deals will they close?":
        "En combien de temps les nouveaux représentants deviennent-ils productifs, et combien de ventes concluront-ils?",
    "How dependent are you on Northern Comfort Group?": "À quel point dépendez-vous de Northern Comfort Group?",
    "Why $4M, and how long does it last?": "Pourquoi 4 M$, et combien de temps cela dure-t-il?",
    "Your forecast treats revenue as cash. How does deferred revenue change your cash plan?":
        "Vos prévisions traitent les revenus comme de la trésorerie. Comment les revenus reportés changent-ils votre plan?",
    "Your plan counts on a $240K SR&ED refund in July 2027. How sure is that?":
        "Votre plan compte sur un remboursement RS&DE de 240 k$ en juillet 2027. Est-ce certain?",
    # investors (named by role)
    "The lead seed fund": "Le fonds d’amorçage principal",
    "The angel operator": "L’investisseur providentiel",
    "The skeptical partner": "L’associé sceptique",
    "The strategic investor": "L’investisseur stratégique",
    "The government-backed fund": "Le fonds soutenu par le gouvernement",
    # Practise
    "Roadblock to practise": "Obstacle à pratiquer",
    "Who's asking": "Qui pose la question",
    "Let's work on <b>{title}</b>. Read the numbers first, then answer like you're in the room. I'll check every figure you say against your books.":
        "Travaillons sur <b>{title}</b>. Lisez d’abord les chiffres, puis répondez comme si vous étiez dans la salle. Je vérifie chaque chiffre dans vos livres.",
    "<b>That's an answer a lead investor writes down.</b> {w} out of 5. Readiness is now {score}/100.":
        "<b>C’est une réponse qu’un investisseur principal prend en note.</b> {w} sur 5. Préparation : {score}/100.",
    "Close: {w} out of 5. One thing to fix: {tip} Try again?": "Presque : {w} sur 5. Une chose à corriger : {tip} On réessaie?",
    "That one would hurt in the room ({w} out of 5), and that's why we practise here first. Start with this: {tip}":
        "Celle-là ferait mal dans la salle ({w} sur 5), c’est pour ça qu’on s’exerce ici d’abord. Commencez par ceci : {tip}",
    "First, understand it: {title}": "D’abord, comprendre : {title}",
    "A strong answer has four parts: the number, how you got it, the weak spot, and what you're doing about it.":
        "Une bonne réponse a quatre parties : le chiffre, comment vous l’avez obtenu, le point faible, et ce que vous faites pour y remédier.",
    "Your answer": "Votre réponse",
    "Get feedback": "Obtenir une rétroaction",
    "Try again": "Réessayer",
    "Attempt {n}": "Tentative {n}",
    # Partner meeting
    "Welcome to my partner meeting. In a real raise, this is the last step: you pitch the whole partnership at once. A lead seed fund partner, an angel investor and the skeptical partner will ask six questions, <b>{secs} seconds</b> each. Every partner has one thing that makes them walk out. It's the hardest version of the meeting, so the real one feels easier.":
        "Bienvenue à ma réunion des associés. Dans une vraie levée de fonds, c’est la dernière étape : vous présentez à tous les associés à la fois. Un associé d’un fonds d’amorçage, un investisseur providentiel et l’associé sceptique poseront six questions, <b>{secs} secondes</b> chacune. Chaque associé a une raison de quitter la salle. C’est la version la plus difficile, pour que la vraie paraisse plus facile.",
    "Walks out when": "Quitte la salle si",
    "Start the partner meeting": "Commencer la réunion des associés",
    "speaking": "parle",
    "listening": "écoute",
    "OUT": "PARTI",
    "Answer": "Répondre",
    # Ask Vicky
    "Ask me anything about your numbers, like 'explain burn multiple like I'm an engineer'. I look everything up in your books, and an independent check reviews my answer before you see it.":
        "Posez-moi toutes vos questions sur vos chiffres, par exemple « explique le multiple de consommation comme à un ingénieur ». Je vérifie tout dans vos livres, et un contrôle indépendant révise ma réponse avant que vous la voyiez.",
    "I need my AI connection to chat, and it isn't set up here. Every number, with its calculation, is in Financials.":
        "J’ai besoin de ma connexion IA pour discuter, et elle n’est pas configurée ici. Chaque chiffre, avec son calcul, se trouve dans Données financières.",
    "Series A": "Série A",
    "Finding": "Constat",
    "Figure": "Chiffre",
    "Source": "Source",
    # source tags
    "Historical": "Historique",
    "Forecast": "Prévision",
    "Founder claim": "Affirmation des fondateurs",
    "Reported in pack": "Déclaré dans le dossier",
    "Public source": "Source publique",
}


def tr(text: str, lang: str = "en", **kw) -> str:
    out = FR.get(text, text) if lang == "fr" else text
    return out.format(**kw) if kw else out


def ai_instruction(lang: str) -> str:
    """Appended to AI requests in French mode. Figures stay as the engine writes them so the audit can check them."""
    if lang != "fr":
        return ""
    return ("\n\n[Language] Reply in Canadian French (français canadien). Keep every figure exactly as written in the "
            "evidence and fact sheet (for example $1.29M, 4.9%, 8.3 months), so the audit can check it.")


MONTHS_FR = {"January": "janvier", "February": "février", "March": "mars", "April": "avril", "May": "mai",
             "June": "juin", "July": "juillet", "August": "août", "September": "septembre", "October": "octobre",
             "November": "novembre", "December": "décembre"}

SPEECH_LANG = {"en": "en-CA", "fr": "fr-CA"}
