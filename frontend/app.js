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
  const titre = couleur ? couleur : "joker : n'importe quelle couleur";
  return `<span class="${classes.join(" ")}" title="${titre}">${couleur ? "" : "?"}</span>`;
}

function coutHtml(cout) {
  return `<span class="cout">${(cout || []).map((c) => deHtml(c, true)).join("")}</span>`;
}

function metaCapacite(capacite) {
  const morceaux = [];
  if (capacite.condition) morceaux.push(`condition : ${capacite.condition}`);
  if (capacite.multiplicateur) morceaux.push(`multiplicateur : ${capacite.multiplicateur}`);
  return morceaux.length ? `<div class="meta">${morceaux.join(" — ")}</div>` : "";
}

function capacitesHtml(personnage, couleurTest) {
  return (personnage.capacites || [])
    .map((capacite) => {
      // Indice visuel : la couleur de De actuellement selectionnee complete-t-elle ce cout ?
      const prete = couleurTest && (personnage.declencheurs || []).includes(couleurTest);
      return `<div class="capacite${prete ? " prete" : ""}">
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
  render(nouvelEtat);
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
  const monTour = etat.joueur_courant === "humain" && !etat.terminee;
  etat.pool.forEach((de) => {
    const el = document.createElement("span");
    el.className = `de de-${de.couleur}`;
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
  document.getElementById("pool-info").textContent =
    `${etat.pool.length} De(s) restant(s) ce round`;
}

function couleurChoisie() {
  const de = etat.pool.find((d) => d.id === deChoisiId);
  return de ? de.couleur : null;
}

function renderEquipes() {
  const couleur = couleurChoisie();
  const monTour = etat.joueur_courant === "humain" && !etat.terminee;

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
  const declenche = couleur && (personnage.declencheurs || []).includes(couleur);
  if (declenche) carte.classList.add("declencheur");

  const reserve = personnage.des_stockes.length
    ? personnage.des_stockes.map((d) => deHtml(d.couleur, true)).join("")
    : `<span class="meta">aucun</span>`;

  carte.innerHTML = `
    <h5>${personnage.nom}
      ${personnage.a_attaque ? '<span class="badge">a attaque</span>' : ""}
      ${declenche ? '<span class="badge indice">declenche une capacite</span>' : ""}
    </h5>
    <p class="archetype">Position ${personnage.position_piste + 1} sur la piste</p>
    ${statsHtml(personnage)}
    ${capacitesHtml(personnage, couleur)}
    <div class="reserve"><span class="libelle">Des stockes</span>${reserve}</div>
  `;

  if (actions) {
    const zone = document.createElement("div");
    zone.className = "actions-perso";

    const btnStock = document.createElement("button");
    btnStock.textContent = "Stocker";
    btnStock.addEventListener("click", () => drafter(personnage.id, "stock"));
    zone.appendChild(btnStock);

    const btnAttaque = document.createElement("button");
    btnAttaque.className = "secondaire";
    btnAttaque.textContent = `Attaquer (${personnage.attaque})`;
    btnAttaque.disabled = personnage.a_attaque;
    btnAttaque.title = personnage.a_attaque
      ? "Une seule attaque par round et par personnage"
      : `Depense le De pour infliger ${personnage.attaque} degats`;
    btnAttaque.addEventListener("click", () => drafter(personnage.id, "attaque"));
    zone.appendChild(btnAttaque);

    carte.appendChild(zone);
  }
  return carte;
}

async function drafter(personnageId, usage) {
  const deId = deChoisiId;
  deChoisiId = null;
  messageErreur = null;
  try {
    const nouvelEtat = await api("/partie/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ de_id: deId, personnage_id: personnageId, usage }),
    });
    render(nouvelEtat);
  } catch (e) {
    messageErreur = e.message;
    render(etat);
  }
}

function renderJournal() {
  const journal = document.getElementById("journal");
  vider(journal);
  etat.journal.forEach((ligne) => {
    const p = document.createElement("p");
    if (ligne.startsWith("---")) p.className = "round";
    else if (ligne.startsWith("CAPACITE")) p.className = "capacite-log";
    else if (ligne.includes(" PV (")) p.className = "pv";
    p.textContent = ligne;
    journal.appendChild(p);
  });
  journal.scrollTop = journal.scrollHeight;
}

function renderConsigne() {
  const consigne = document.getElementById("consigne");
  consigne.className = "consigne";
  vider(consigne);

  if (messageErreur) {
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
  if (etat.joueur_courant !== "humain") {
    consigne.textContent = "L'IA drafte...";
    return;
  }
  const creneau = etat.sequence.find((c) => c.courant);
  const prefixe = creneau ? `Creneau de ${creneau.nom} : ` : "";
  consigne.textContent = deChoisiId
    ? `${prefixe}choisis le Personnage qui recoit ce De, puis Stocker ou Attaquer.`
    : `${prefixe}clique un De du pool.`;
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
