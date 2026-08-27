// Urban Eredan — Eredice : frontend vanilla, jouable uniquement au clic.

const API = "/api";
const TAILLE_EQUIPE = 3;

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

let personnages = [];
const equipeSelectionnee = new Set();
let etat = null;
let deChoisiId = null;
let messageErreur = null;
// Nombre d'actions de draft deja affichees : sert a ne mettre en avant (pulsation des
// cartes) que les Capacites declenchees depuis le dernier rendu.
let nbActionsVues = 0;
// Empeche deux sequences de creneaux IA de tourner en parallele.
let iaEnCours = false;

// -------------------------------------------------------------- utilitaires

async function api(chemin, options) {
  const reponse = await fetch(API + chemin, options);
  const data = await reponse.json();
  if (!reponse.ok) throw new Error(data.erreur || "Erreur inconnue");
  return data;
}

function vider(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function deHtml(couleur, petit = false) {
  const classes = ["de", couleur ? `de-${couleur}` : "de-joker"];
  if (petit) classes.push("de-petit");
  const estEpee = couleur === "epee";
  const titre = estEpee
    ? "epee : declenche une attaque"
    : couleur || "joker : n'importe quelle couleur";
  const contenu = estEpee ? "⚔" : couleur ? "" : "?";
  return `<span class="${classes.join(" ")}" title="${titre}">${contenu}</span>`;
}

function coutHtml(cout) {
  return `<span class="cout">${(cout || []).map((c) => deHtml(c, true)).join("")}</span>`;
}

function nomJoueur(cle) {
  return cle === "humain" ? "Toi" : "IA";
}

function mouvementReduit() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function pause(ms) {
  return new Promise((resoudre) => setTimeout(resoudre, ms));
}

function actionsJournal(unEtat) {
  return (unEtat.journal || []).flatMap((r) => r.entrees.filter((e) => e.genre === "action"));
}

function metaCapacite(capacite) {
  const morceaux = [];
  if (capacite.condition) morceaux.push(`condition : ${capacite.condition}`);
  if (capacite.multiplicateur) morceaux.push(`multiplicateur : ${capacite.multiplicateur}`);
  return morceaux.length ? `<div class="meta">${morceaux.join(" — ")}</div>` : "";
}

function capacitesHtml(personnage, couleurTest, indicesChoix = []) {
  return (personnage.capacites || [])
    .map((capacite, i) => {
      // Indice visuel : la couleur de De actuellement selectionnee complete-t-elle ce cout ?
      const prete = couleurTest && (personnage.declencheurs || []).includes(couleurTest);
      const enChoix = indicesChoix.includes(i);
      return `<div class="capacite${prete ? " prete" : ""}${enChoix ? " en-choix" : ""}">
        ${coutHtml(capacite.cout)}${capacite.description}
        ${metaCapacite(capacite)}
      </div>`;
    })
    .join("");
}

function statsHtml(personnage) {
  const majore = personnage.bonus_attaque ? " majore" : "";
  const detail = personnage.bonus_attaque
    ? ` <span class="badge">base ${personnage.attaque_base}</span>`
    : "";
  return `<div class="stats">
    <span>Initiative <b>${personnage.initiative}</b></span>
    <span class="${majore.trim()}">Attaque <b>${personnage.attaque}</b>${detail}</span>
  </div>`;
}

// ------------------------------------------------------- ecran de selection

async function initSelection() {
  personnages = await api("/personnages");
  equipeSelectionnee.clear();
  renderSelection();
}

function renderSelection() {
  const grille = document.getElementById("grille-selection");
  vider(grille);
  personnages
    .slice()
    .sort((a, b) => a.initiative - b.initiative)
    .forEach((p) => {
      const carte = document.createElement("div");
      carte.className = "carte-personnage selectionnable";
      if (equipeSelectionnee.has(p.id)) carte.classList.add("selectionnee");
      carte.innerHTML = `<h5>${p.nom}</h5>${statsHtml({ ...p, attaque: p.attaque, attaque_base: p.attaque, bonus_attaque: 0 })}${capacitesHtml(p, null)}`;
      carte.addEventListener("click", () => {
        if (equipeSelectionnee.has(p.id)) equipeSelectionnee.delete(p.id);
        else if (equipeSelectionnee.size < TAILLE_EQUIPE) equipeSelectionnee.add(p.id);
        renderSelection();
      });
      grille.appendChild(carte);
    });
  document.getElementById("compteur-selection").textContent =
    `${equipeSelectionnee.size} / ${TAILLE_EQUIPE} selectionnes`;
  document.getElementById("btn-lancer-partie").disabled =
    equipeSelectionnee.size !== TAILLE_EQUIPE;
}

document.getElementById("btn-equipe-aleatoire").addEventListener("click", () => {
  equipeSelectionnee.clear();
  const pioche = personnages.slice();
  while (equipeSelectionnee.size < TAILLE_EQUIPE && pioche.length > 0) {
    const [tire] = pioche.splice(Math.floor(Math.random() * pioche.length), 1);
    equipeSelectionnee.add(tire.id);
  }
  renderSelection();
});

document.getElementById("btn-lancer-partie").addEventListener("click", async () => {
  const nouvelEtat = await api("/partie", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ equipe: Array.from(equipeSelectionnee) }),
  });
  ecranSelection.classList.add("cache");
  ecranPartie.classList.remove("cache");
  deChoisiId = null;
  messageErreur = null;
  nbActionsVues = 0;
  render(nouvelEtat);
  poursuivreIa();
});

document.getElementById("btn-nouvelle-partie").addEventListener("click", async () => {
  ecranFin.classList.add("cache");
  ecranSelection.classList.remove("cache");
  await initSelection();
});

// ------------------------------------------------------------- ecran match

function render(nouvelEtat) {
  etat = nouvelEtat;
  renderTableauBord();
  renderPiste();
  renderPool();
  renderEquipes();
  renderJournal();
  renderConsigne();

  const actions = actionsJournal(etat);
  pulserCapacites(actions.slice(nbActionsVues));
  nbActionsVues = actions.length;
}

function renderTableauBord() {
  [["humain", etat.joueur_humain], ["ia", etat.joueur_ia]].forEach(([cle, joueur]) => {
    const ratio = Math.max(0, Math.min(1, joueur.pv / joueur.pv_depart));
    document.querySelector(`#pv-${cle}-jauge span`).style.width = `${ratio * 100}%`;
    document.getElementById(`pv-${cle}-texte`).textContent = `${joueur.pv} PV`;
  });
  document.getElementById("round-texte").textContent =
    `Round ${etat.round} / ${etat.rounds_max} max`;
}

function renderPiste() {
  const piste = document.getElementById("piste");
  vider(piste);
  etat.sequence.forEach((creneau, i) => {
    const el = document.createElement("div");
    el.className = `creneau ${creneau.proprietaire}`;
    if (creneau.joue) el.classList.add("joue");
    if (creneau.courant) el.classList.add("courant");
    el.innerHTML = `<span class="num">${i + 1}</span>${creneau.nom}`;
    el.title = creneau.proprietaire === "humain" ? "Ton creneau de draft" : "Creneau de l'IA";
    piste.appendChild(el);
  });
}

function renderPool() {
  const pool = document.getElementById("pool");
  vider(pool);
  // Un choix de Capacite en attente gele le draft : il faut le trancher d'abord.
  const monTour =
    etat.joueur_courant === "humain" && !etat.terminee && !etat.choix_capacite;
  etat.pool.forEach((de) => {
    const el = document.createElement("span");
    el.className = `de de-${de.couleur}`;
    el.textContent = de.couleur === "epee" ? "⚔" : "";
    el.title = de.couleur === "epee" ? "epee : declenche une attaque" : de.couleur;
    el.dataset.de = de.id;
    if (monTour) el.classList.add("cliquable");
    if (de.id === deChoisiId) el.classList.add("choisi");
    if (monTour) {
      el.addEventListener("click", () => {
        deChoisiId = de.id === deChoisiId ? null : de.id;
        messageErreur = null;
        render(etat);
      });
    }
    pool.appendChild(el);
  });
  const n = etat.pool.length;
  document.getElementById("pool-info").textContent =
    n === 1 ? "1 De restant ce round" : `${n} Des restants ce round`;
}

function couleurChoisie() {
  const de = etat.pool.find((d) => d.id === deChoisiId);
  return de ? de.couleur : null;
}

function renderEquipes() {
  const couleur = couleurChoisie();
  const monTour =
    etat.joueur_courant === "humain" && !etat.terminee && !etat.choix_capacite;

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((p) => {
    grilleHumain.appendChild(carteEnJeu(p, { couleur, actions: monTour && deChoisiId !== null }));
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((p) => {
    grilleIa.appendChild(carteEnJeu(p, { couleur: null, actions: false }));
  });
}

function carteEnJeu(personnage, { couleur, actions }) {
  const carte = document.createElement("div");
  carte.className = "carte-personnage";
  carte.dataset.personnage = personnage.id;
  const declenche = couleur && (personnage.declencheurs || []).includes(couleur);
  if (declenche) carte.classList.add("declencheur");
  const choix = etat.choix_capacite;
  const enChoix = Boolean(choix) && choix.personnage_id === personnage.id;
  if (enChoix) carte.classList.add("en-choix");

  const reserve = personnage.des_stockes.length
    ? personnage.des_stockes.map((d) => deHtml(d.couleur, true)).join("")
    : `<span class="meta">aucun</span>`;

  carte.innerHTML = `
    <h5>${personnage.nom}
      ${declenche ? '<span class="badge indice">declenche une capacite</span>' : ""}
    </h5>
    <p class="archetype">Position ${personnage.position_piste + 1} sur la piste</p>
    ${statsHtml(personnage)}
    ${capacitesHtml(personnage, couleur, enChoix ? choix.options.map((o) => o.indice) : [])}
    <div class="reserve"><span class="libelle">Des stockes</span>${reserve}</div>
  `;

  if (actions) {
    const zone = document.createElement("div");
    zone.className = "actions-perso";
    const estEpee = couleur === "epee";

    if (estEpee) {
      const btnAttaque = document.createElement("button");
      btnAttaque.textContent = `Attaquer (${personnage.attaque})`;
      btnAttaque.title = `Depense l'epee pour infliger ${personnage.attaque} degats`;
      btnAttaque.addEventListener("click", () => drafter(personnage.id, "attaque", carte));
      zone.appendChild(btnAttaque);
    } else {
      const btnStock = document.createElement("button");
      btnStock.textContent = "Stocker";
      btnStock.title = "Stocke ce De sur le Personnage -- s'il n'a aucune Capacite de "
        + "cette couleur, le De est perdu";
      btnStock.addEventListener("click", () => drafter(personnage.id, "stock", carte));
      zone.appendChild(btnStock);
    }

    carte.appendChild(zone);
  }
  return carte;
}

async function drafter(personnageId, usage, carteEl) {
  const deId = deChoisiId;
  // Les positions doivent etre relevees avant tout re-rendu : on lance donc le vol du De
  // maintenant, et on n'affiche le nouvel etat qu'une fois l'animation et la requete
  // terminees toutes les deux.
  const vol = animerTransfert(document.querySelector("#pool .de.choisi"), carteEl, usage,
                              couleurChoisie());
  deChoisiId = null;
  messageErreur = null;
  try {
    const [nouvelEtat] = await Promise.all([
      api("/partie/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ de_id: deId, personnage_id: personnageId, usage }),
      }),
      vol,
    ]);
    render(nouvelEtat);
    poursuivreIa();
  } catch (e) {
    messageErreur = e.message;
    render(etat);
  }
}

/** Tranche un choix entre plusieurs Capacites payables : la cascade d'activations
 *  suspendue cote serveur reprend alors son cours. */
async function choisirCapacite(indice) {
  messageErreur = null;
  try {
    const nouvelEtat = await api("/partie/choix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ indice }),
    });
    render(nouvelEtat);
    // L'activation choisie s'ajoute a une action de draft deja affichee : `render` ne la
    // voit donc pas comme nouvelle, on declenche la mise en avant a la main.
    pulserCapacites(actionsJournal(nouvelEtat).slice(-1));
    poursuivreIa();
  } catch (e) {
    messageErreur = e.message;
    render(etat);
  }
}

/** Point d'arrivee du De : juste apres les Des deja stockes de la carte cible. */
function pointArrivee(carteEl, usage) {
  if (usage === "attaque") {
    const rect = carteEl.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }
  const reserve = carteEl.querySelector(".reserve");
  const pastilles = reserve ? reserve.querySelectorAll(".de-petit") : [];
  if (pastilles.length) {
    const rect = pastilles[pastilles.length - 1].getBoundingClientRect();
    return { x: rect.right + 8, y: rect.top + rect.height / 2 };
  }
  const rect = (reserve || carteEl).getBoundingClientRect();
  return { x: rect.left + 78, y: rect.top + rect.height / 2 };
}

/** Fait voler un clone du De drafte depuis le pool jusqu'a sa cible. `stock` : le De se
 *  pose dans la reserve du Personnage ; `attaque` : le De est consomme, il vient
 *  s'ecraser sur la carte et disparait. */
function animerTransfert(deEl, carteEl, usage, couleur, duree) {
  if (!deEl || !carteEl || !couleur || mouvementReduit() || !deEl.animate) {
    return Promise.resolve();
  }
  const consomme = usage === "attaque";
  const depart = deEl.getBoundingClientRect();
  const arrivee = pointArrivee(carteEl, usage);
  const dx = arrivee.x - (depart.left + depart.width / 2);
  const dy = arrivee.y - (depart.top + depart.height / 2);

  const clone = document.createElement("span");
  clone.className = `de de-${couleur} de-en-vol`;
  clone.style.left = `${depart.left}px`;
  clone.style.top = `${depart.top}px`;
  clone.style.width = `${depart.width}px`;
  clone.style.height = `${depart.height}px`;
  document.body.appendChild(clone);

  const etapes = consomme
    ? [
        { transform: "translate(0, 0) scale(1)", opacity: 1 },
        { transform: `translate(${dx}px, ${dy}px) scale(1.45)`, opacity: 1, offset: 0.72 },
        { transform: `translate(${dx}px, ${dy}px) scale(0.2)`, opacity: 0 },
      ]
    : [
        { transform: "translate(0, 0) scale(1) rotate(0deg)" },
        {
          transform: `translate(${dx * 0.55}px, ${dy * 0.55 - 30}px) scale(1.2) rotate(-12deg)`,
          offset: 0.55,
        },
        { transform: `translate(${dx}px, ${dy}px) scale(0.55) rotate(0deg)` },
      ];
  const animation = clone.animate(etapes, {
    duration: duree || (consomme ? 520 : 470),
    easing: "cubic-bezier(.34, .78, .28, 1)",
  });
  return animation.finished.catch(() => {}).then(() => clone.remove());
}

/** Anime le De que l'IA vient de drafter, en partant de sa place dans le pool tel qu'il
 *  est encore affiche (le nouvel etat n'est rendu qu'apres l'animation). */
function animerActionIa(action, poolAvant, poolApres) {
  if (!action) return Promise.resolve();
  // Le De drafte est celui qui a disparu du pool ; on se rabat sur la couleur si le
  // diff est ambigu (une Capacite peut avoir retire un second De du pool).
  const restants = new Set(poolApres.map((d) => d.id));
  const retire = poolAvant.find((d) => !restants.has(d.id) && d.couleur === action.de);
  const deEl = (retire && document.querySelector(`#pool .de[data-de="${retire.id}"]`))
    || document.querySelector(`#pool .de-${action.de}`);
  const carte = document.querySelector(`#equipe-ia [data-personnage="${action.personnage_id}"]`);
  return animerTransfert(deEl, carte, action.usage, action.de, 420);
}

/** Deroule les creneaux de l'IA un par un, en animant chaque choix comme ceux du joueur.
 *  Le backend ne resout qu'un creneau par appel, ce qui donne un etat reel a animer entre
 *  chaque pick au lieu d'un bloc de coups deja joues. */
async function poursuivreIa() {
  if (iaEnCours) return;
  iaEnCours = true;
  try {
    while (etat && !etat.terminee && etat.joueur_courant === "ia") {
      await pause(200);
      const poolAvant = etat.pool;
      const nouvelEtat = await api("/partie/ia", { method: "POST" });
      const actions = actionsJournal(nouvelEtat);
      await animerActionIa(actions[actions.length - 1], poolAvant, nouvelEtat.pool);
      render(nouvelEtat);
    }
  } catch (e) {
    messageErreur = e.message;
    render(etat);
  } finally {
    iaEnCours = false;
  }
}

/** Met en avant les cartes dont une Capacite vient de se declencher. */
function pulserCapacites(nouvellesActions) {
  const ids = new Set();
  nouvellesActions.forEach((action) => {
    (action.consequences || []).forEach((c) => {
      if (c.type === "capacite" && c.personnage_id) ids.add(c.personnage_id);
    });
  });
  ids.forEach((id) => {
    document.querySelectorAll(`[data-personnage="${id}"]`).forEach((el) => {
      el.classList.remove("pulse");
      void el.offsetWidth; // force le redemarrage de l'animation CSS
      el.classList.add("pulse");
      setTimeout(() => el.classList.remove("pulse"), 900);
    });
  });
}

const ICONES = { capacite: "\u26a1", pv: "\u2665", attaque: "\u00b1", initiative: "\u2195",
                 de: "\u2b22", choix: "\u21c4", de_perdu: "\u2717" };

function echapper(valeur) {
  const div = document.createElement("div");
  div.textContent = valeur == null ? "" : String(valeur);
  return div.innerHTML;
}

/** Une consequence d'une action : Capacite declenchee, PV, manipulation de Des... */
function consequenceHtml(c) {
  const icone = ICONES[c.type] || "\u00b7";
  let corps;
  if (c.type === "pv") {
    const signe = c.delta > 0 ? "+" : "\u2212";
    corps = `<b>${nomJoueur(c.joueur)}</b> `
      + `<span class="delta ${c.delta > 0 ? "gain" : "perte"}">${signe}${Math.abs(c.delta)} PV</span> `
      + `<span class="mini">${c.avant} \u2192 ${c.apres}</span>`;
  } else if (c.type === "capacite") {
    const mult = c.multiplicateur && c.multiplicateur !== 1
      ? ` <span class="mini">\u00d7${c.multiplicateur}</span>` : "";
    corps = `<b>${echapper(c.personnage)}</b> \u2014 ${echapper(c.description)}${mult}`
      + ` ${coutHtml(c.cout_paye)}`;
  } else if (c.type === "de" && c.couleur) {
    corps = `${echapper(c.texte)} ${deHtml(c.couleur, true)}`;
  } else {
    corps = echapper(c.texte);
  }
  return `<li class="c-${c.type}"><span class="icone">${icone}</span><span>${corps}</span></li>`;
}

/** Une action de draft : qui a joue, quel De, sur quel Personnage, pour quel usage. */
function actionHtml(action) {
  let usage;
  if (action.usage === "attaque") {
    usage = `<span class="badge badge-attaque">attaque ${action.degats}</span>`;
  } else if (action.perdu) {
    usage = `<span class="badge badge-perdu">De perdu</span>`;
  } else {
    usage = `<span class="badge">stocke (${action.des_stockes})</span>`;
  }
  const consequences = (action.consequences || []).map(consequenceHtml).join("");
  return `<div class="entree action ${action.joueur}">
    <div class="action-entete">
      <span class="qui">${nomJoueur(action.joueur)}</span>
      <span class="mini creneau">creneau ${echapper(action.creneau)}</span>
      ${deHtml(action.de, true)}
      <span class="fleche">\u2192</span>
      <span class="cible">${echapper(action.personnage)}</span>
      ${usage}
    </div>
    ${consequences ? `<ul class="consequences">${consequences}</ul>` : ""}
  </div>`;
}

function evenementHtml(e) {
  if (e.type === "fin_round") {
    return `<div class="entree evenement"><span class="icone">\u231b</span>
      <span>Des non draftes, defausses : ${(e.des || []).map((c) => deHtml(c, true)).join("")}</span>
    </div>`;
  }
  const classe = e.type === "fin_match" ? " fin-match" : "";
  return `<div class="entree evenement${classe}">
    <span class="icone">\u00b7</span><span>${echapper(e.texte)}</span>
  </div>`;
}

function roundHtml(round) {
  // Anti-chronologique comme le journal entier : l'entree la plus recente du round en
  // premier. Les consequences d'une action gardent en revanche leur ordre de resolution,
  // qui se lit comme un enchainement.
  const entrees = round.entrees
    .map((e) => (e.genre === "action" ? actionHtml(e) : evenementHtml(e)))
    .reverse()
    .join("");
  return `<section class="round-bloc">
    <header class="round-entete">
      <span class="round-titre">Round ${round.numero}</span>
      <span class="des-tires">${(round.des_tires || []).map((c) => deHtml(c, true)).join("")}</span>
    </header>
    ${entrees}
  </section>`;
}

function renderJournal() {
  const journal = document.getElementById("journal");
  // Le journal se lit du plus recent au plus ancien : le round en cours est en haut, le
  // preambule de mise en place tout en bas. Ce qui vient de se passer est donc toujours
  // visible sans scroller. `slice()` avant `reverse()` : `etat.journal` reste dans son
  // ordre chronologique, dont dependent `actionsJournal` et le compteur d'actions vues.
  journal.innerHTML =
    (etat.journal || []).slice().reverse().map(roundHtml).join("")
    + (etat.preambule || [])
      .map((e) => `<div class="entree evenement preambule">${echapper(e.texte)}</div>`)
      .join("");
  journal.scrollTop = 0;
}

function renderConsigne() {
  const consigne = document.getElementById("consigne");
  consigne.className = "consigne";
  vider(consigne);

  // Le message d'erreur ne doit pas masquer une invite de choix : sans les boutons, le
  // joueur n'aurait plus aucun moyen de debloquer son creneau.
  if (messageErreur && !etat.choix_capacite) {
    consigne.className = "consigne erreur";
    consigne.textContent = messageErreur;
    return;
  }
  if (etat.terminee) {
    const btn = document.createElement("button");
    btn.textContent = "Voir le resultat final";
    btn.addEventListener("click", renderFin);
    consigne.appendChild(btn);
    return;
  }
  const choix = etat.choix_capacite;
  if (choix) {
    consigne.className = "consigne choix";
    const libelle = document.createElement("span");
    libelle.innerHTML = `<b>${echapper(choix.nom)}</b> : ${choix.options.length} Capacites `
      + "sont payables en meme temps, choisis celle qui s'active.";
    consigne.appendChild(libelle);
    choix.options.forEach((option) => {
      const btn = document.createElement("button");
      btn.className = "secondaire";
      btn.innerHTML = `${echapper(option.description)} <span class="mini">paye `
        + `${option.paiement.map((c) => deHtml(c, true)).join("")}</span>`;
      btn.title = "Seuls ces Des sont defausses ; le reste de la reserve est conserve.";
      btn.addEventListener("click", () => choisirCapacite(option.indice));
      consigne.appendChild(btn);
    });
    if (messageErreur) {
      const erreur = document.createElement("span");
      erreur.className = "erreur-choix";
      erreur.textContent = messageErreur;
      consigne.appendChild(erreur);
    }
    return;
  }
  if (etat.joueur_courant !== "humain") {
    consigne.textContent = "L'IA drafte...";
    return;
  }
  const creneau = etat.sequence.find((c) => c.courant);
  const prefixe = creneau ? `Creneau de ${creneau.nom} : ` : "";
  if (!deChoisiId) {
    consigne.textContent = `${prefixe}clique un De du pool.`;
    return;
  }
  const action = couleurChoisie() === "epee" ? "Attaquer" : "Stocker";
  consigne.textContent = `${prefixe}choisis le Personnage qui recoit ce De, puis ${action}.`;
}

function renderFin() {
  ecranPartie.classList.add("cache");
  ecranFin.classList.remove("cache");
  const titre = document.getElementById("titre-fin");
  if (etat.vainqueur === "humain") titre.textContent = "Victoire !";
  else if (etat.vainqueur === "ia") titre.textContent = "Defaite...";
  else titre.textContent = "Egalite";
  document.getElementById("detail-fin").textContent =
    `Toi : ${etat.joueur_humain.pv} PV — IA : ${etat.joueur_ia.pv} PV (${etat.round} rounds)`;
}

// ------------------------------------------------------------------- start
initSelection();
