// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

const elPvHumainTexte = document.getElementById("pv-humain-texte");
const elPvIaTexte = document.getElementById("pv-ia-texte");
const elPvHumainRonds = document.getElementById("pv-humain-ronds");
const elPvIaRonds = document.getElementById("pv-ia-ronds");
const elDuelNumeroTexte = document.getElementById("duel-numero-texte");

const elEquipeHumain = document.getElementById("equipe-humain");
const elEquipeIa = document.getElementById("equipe-ia");

const elZonePioche = document.getElementById("zone-pioche");
const elZoneResultat = document.getElementById("zone-resultat");
const elMessageAttente = document.getElementById("message-attente");
const elCombattantsEnDuel = document.getElementById("combattants-en-duel");
const elJournalResolution = document.getElementById("journal-resolution");
const elBtnDuelSuivant = document.getElementById("btn-duel-suivant");

const elPiocheTasRestant = document.getElementById("pioche-tas-restant");
const elMesCartesPiochees = document.getElementById("mes-cartes-piochees");
const elMesTotauxPioche = document.getElementById("mes-totaux-pioche");
const elIaCartesPiochees = document.getElementById("ia-cartes-piochees");
const elStatutPiocheIa = document.getElementById("statut-pioche-ia");
const elBtnPiocher = document.getElementById("btn-piocher");
const elBtnArreter = document.getElementById("btn-arreter");

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;

const NIVEAU_TOTAL_MAX = 8;

// -------------------------------------------------------------- utilitaires

async function api(path, options) {
  const reponse = await fetch(API + path, options);
  const data = await reponse.json();
  if (!reponse.ok) {
    throw new Error(data.erreur || "Erreur inconnue");
  }
  return data;
}

function vider(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function trouverCombattant(etat, id) {
  return (
    etat.joueur_humain.equipe.find((c) => c.id === id) ||
    etat.joueur_ia.equipe.find((c) => c.id === id)
  );
}

function niveauCombattant(id) {
  const c = combattantsDisponibles.find((c) => c.id === id);
  return c ? c.niveau : 0;
}

function sommeNiveauxSelection() {
  return Array.from(equipeSelectionnee).reduce((somme, id) => somme + niveauCombattant(id), 0);
}

function conditionEstValidee(pouvoir, role, pvSoi, pvAdv) {
  if (!pouvoir) return false;
  switch (pouvoir.condition) {
    case "courage":
      return role === "j1";
    case "riposte":
      return role === "j2";
    case "vengeance":
      return pvAdv > pvSoi;
    case "domination":
      return pvAdv < pvSoi;
    default:
      return false;
  }
}

function echapperHtml(texte) {
  const div = document.createElement("div");
  div.textContent = texte;
  return div.innerHTML;
}

// La condition n'est surlignee en rouge que si pouvoir.condition est reellement
// definie cote donnees (sinon certains textes commencent par un mot-cle sans
// que ce soit une vraie condition de jeu, ex. "Patience : ..." chez Grind).
function formaterTexteCompetence(pouvoir) {
  const description = pouvoir ? pouvoir.description : "";
  if (pouvoir && pouvoir.condition) {
    const indexDeuxPoints = description.indexOf(":");
    if (indexDeuxPoints !== -1) {
      const avant = description.slice(0, indexDeuxPoints + 1);
      const apres = description.slice(indexDeuxPoints + 1);
      return `<span class="cond">${echapperHtml(avant)}</span>${echapperHtml(apres)}`;
    }
  }
  return echapperHtml(description);
}

function creerCarteCombattant(data, { selectionnable = false, selectionnee = false, active = false, conditionValidee = false, indisponible = false, onClick = null } = {}) {
  const carte = document.createElement("div");
  carte.className = "carte-combattant";
  if (selectionnable) carte.classList.add("selectionnable");
  if (selectionnee) carte.classList.add("selectionnee");
  if (active) carte.classList.add("active-duel");
  if (conditionValidee) carte.classList.add("condition-validee");
  if (data.utilise) carte.classList.add("utilisee");
  if (indisponible) carte.classList.add("indisponible");

  const top = document.createElement("div");
  top.className = "cc-top";
  if (data.image) {
    top.innerHTML = `<div class="cc-emblem"><img src="/img/${encodeURIComponent(data.image)}" alt=""></div>`;
  }
  const nom = document.createElement("h4");
  nom.className = "cc-nom";
  nom.textContent = data.nom;
  top.appendChild(nom);
  if (data.niveau) {
    const niveau = document.createElement("span");
    niveau.className = "cc-niveau";
    niveau.title = `Niveau ${data.niveau} / 3`;
    niveau.textContent = "★".repeat(data.niveau) + "☆".repeat(3 - data.niveau);
    top.appendChild(niveau);
  }
  carte.appendChild(top);

  const band = document.createElement("div");
  band.className = "cc-band";
  band.innerHTML = `<p>${formaterTexteCompetence(data.pouvoir)}</p>`;
  carte.appendChild(band);

  const stats = document.createElement("div");
  stats.className = "cc-stats";
  stats.innerHTML = `
    <div class="cc-stat"><b>${data.puissance}</b><span>Puissance</span></div>
    <div class="cc-stat"><b>${data.degats}</b><span>Degats</span></div>
  `;
  carte.appendChild(stats);

  if (data.utilise) {
    const badge = document.createElement("span");
    badge.className = "badge-utilise";
    badge.textContent = "Utilise";
    carte.appendChild(badge);
  }

  if (onClick) carte.addEventListener("click", onClick);
  return carte;
}

function formaterDetailListe(detail) {
  return detail
    .map(([label, valeur], i) => {
      const texte = i === 0 ? `${valeur}` : `${valeur >= 0 ? "+" : "-"} ${Math.abs(valeur)}`;
      return `<li>${texte} <span class="detail-label">(${label})</span></li>`;
    })
    .join("");
}

// Icone + jauge de pastilles a la place d'un texte de stats : une carte
// Puissance se lit visuellement (forme + couleur + nombre de pastilles
// pleines), le nom ne reste que dans le title (tooltip) et un petit libelle.
const REGEX_DIACRITIQUES = new RegExp("[\\u0300-\\u036f]", "g");

function normaliserNomCarte(nom) {
  return nom.normalize("NFD").replace(REGEX_DIACRITIQUES, "").toLowerCase();
}

function creerLignePips(valeur, max, type) {
  const ligne = document.createElement("span");
  ligne.className = "cp-pips-ligne";
  for (let i = 0; i < max; i++) {
    const pip = document.createElement("span");
    pip.className = `cp-pip cp-pip-${type}` + (i < valeur ? " cp-pip--on" : "");
    ligne.appendChild(pip);
  }
  return ligne;
}

function creerCartePuissance(carte, { mini = false } = {}) {
  const type = normaliserNomCarte(carte.nom);
  const el = document.createElement("div");
  el.className = `carte-puissance carte-puissance--${type}` + (mini ? " carte-puissance--mini" : "");
  el.title = `${carte.nom} : ${carte.puissance} Puissance / ${carte.malus} Malus`;

  const icone = document.createElement("span");
  icone.className = "cp-icone";
  icone.setAttribute("aria-hidden", "true");
  el.appendChild(icone);

  const pips = document.createElement("div");
  pips.className = "cp-pips";
  pips.appendChild(creerLignePips(carte.puissance, 2, "puissance"));
  pips.appendChild(creerLignePips(carte.malus, 2, "malus"));
  el.appendChild(pips);

  const label = document.createElement("span");
  label.className = "cp-label";
  label.textContent = carte.nom;
  el.appendChild(label);

  return el;
}

// Carte cachee (dos), utilisee pour montrer que l'adversaire IA a bien
// pioche des cartes pendant la phase de pioche en cours, sans en reveler
// le contenu avant la resolution du duel.
function creerCartePuissanceDos() {
  const el = document.createElement("div");
  el.className = "carte-puissance carte-puissance--dos";
  el.title = "Carte cachee";
  el.setAttribute("aria-hidden", "true");
  return el;
}

// ------------------------------------------------------- ecran de selection

async function initSelectionEcran() {
  combattantsDisponibles = await api("/combattants");
  equipeSelectionnee.clear();
  renderGrilleSelection();
}

function peutAjouterAuBudget(c, niveauTotal) {
  return equipeSelectionnee.size < 4 && niveauTotal + c.niveau <= NIVEAU_TOTAL_MAX;
}

function renderGrilleSelection() {
  const grille = document.getElementById("grille-selection");
  vider(grille);
  const niveauTotal = sommeNiveauxSelection();
  combattantsDisponibles.forEach((c) => {
    const estSelectionnee = equipeSelectionnee.has(c.id);
    const estDisponible = estSelectionnee || peutAjouterAuBudget(c, niveauTotal);
    const carte = creerCarteCombattant(
      { ...c, utilise: false },
      {
        selectionnable: estDisponible,
        selectionnee: estSelectionnee,
        indisponible: !estDisponible,
        onClick: estDisponible ? () => toggleSelection(c.id) : null,
      }
    );
    grille.appendChild(carte);
  });
  const compteur = document.getElementById("compteur-selection");
  compteur.textContent = `${equipeSelectionnee.size} / 4 selectionnes — Niveau ${niveauTotal} / ${NIVEAU_TOTAL_MAX}`;
  document.getElementById("btn-lancer-partie").disabled =
    equipeSelectionnee.size !== 4 || niveauTotal > NIVEAU_TOTAL_MAX;
}

function toggleSelection(id) {
  if (equipeSelectionnee.has(id)) {
    equipeSelectionnee.delete(id);
  } else {
    const c = combattantsDisponibles.find((c) => c.id === id);
    if (c && peutAjouterAuBudget(c, sommeNiveauxSelection())) equipeSelectionnee.add(id);
  }
  renderGrilleSelection();
}

// Tirage aleatoire d'une equipe qui utilise tout le budget de niveaux : on
// enumere toutes les combinaisons de 4 Combattants (22 choisir 4 reste petit),
// on ne garde que celles dont la somme des niveaux est la plus haute possible
// sans depasser le budget (donc = NIVEAU_TOTAL_MAX des qu'une telle equipe
// existe), puis on en tire une au hasard parmi elles.
function selectionnerEquipeAleatoire() {
  const ids = combattantsDisponibles.map((c) => c.id);
  const combinaisons = [];
  for (let a = 0; a < ids.length; a++) {
    for (let b = a + 1; b < ids.length; b++) {
      for (let c = b + 1; c < ids.length; c++) {
        for (let d = c + 1; d < ids.length; d++) {
          const combo = [ids[a], ids[b], ids[c], ids[d]];
          const somme = combo.reduce((s, id) => s + niveauCombattant(id), 0);
          if (somme <= NIVEAU_TOTAL_MAX) combinaisons.push({ combo, somme });
        }
      }
    }
  }
  const meilleureSomme = Math.max(...combinaisons.map((c) => c.somme));
  const meilleuresCombinaisons = combinaisons.filter((c) => c.somme === meilleureSomme);
  const { combo: equipeChoisie } = meilleuresCombinaisons[Math.floor(Math.random() * meilleuresCombinaisons.length)];
  equipeSelectionnee.clear();
  equipeChoisie.forEach((id) => equipeSelectionnee.add(id));
  renderGrilleSelection();
}

document.getElementById("btn-selection-aleatoire").addEventListener("click", selectionnerEquipeAleatoire);

document.getElementById("btn-lancer-partie").addEventListener("click", async () => {
  const etat = await api("/partie", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ equipe: Array.from(equipeSelectionnee) }),
  });
  ecranSelection.classList.add("cache");
  ecranPartie.classList.remove("cache");
  render(etat);
});

document.getElementById("btn-nouvelle-partie").addEventListener("click", async () => {
  ecranFin.classList.add("cache");
  ecranSelection.classList.remove("cache");
  await initSelectionEcran();
});

// ------------------------------------------------------------- ecran partie

function peutChoisirMaintenant(etat) {
  const humainSlot = humanRole(etat);
  const humainChoisiId = etat["combattant_" + humainSlot];
  return etat.phase === "choix_combattant" && humainChoisiId === null;
}

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderEquipes(etat);
  renderZoneCentrale(etat);
}

function pvRonds(pv) {
  const total = 10;
  const pvSecur = Math.max(0, pv);
  const orangeCount = pvSecur > total ? Math.min(pvSecur - total, total) : 0;
  const pleinCount = pvSecur > total ? total - orangeCount : pvSecur;
  let html = "";
  for (let i = 0; i < total; i++) {
    const classe = i < orangeCount ? "orange" : i < orangeCount + pleinCount ? "plein" : "";
    html += `<span class="pv-rond ${classe}"></span>`;
  }
  return html;
}

function renderTableauBord(etat) {
  const pvH = etat.joueur_humain.pv;
  const pvI = etat.joueur_ia.pv;
  elPvHumainTexte.textContent = `${pvH} PV`;
  elPvIaTexte.textContent = `${pvI} PV`;
  elPvHumainRonds.innerHTML = pvRonds(pvH);
  elPvIaRonds.innerHTML = pvRonds(pvI);
  elDuelNumeroTexte.textContent = `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function renderEquipe(grille, equipe, { peutChoisir = false, role, pvSoi, pvAdv, combattantJ1, combattantJ2 } = {}) {
  vider(grille);
  equipe.forEach((c) => {
    const active = c.id === combattantJ1 || c.id === combattantJ2;
    const selectionnable = peutChoisir && !c.utilise;
    grille.appendChild(
      creerCarteCombattant(c, {
        selectionnable,
        active,
        conditionValidee: conditionEstValidee(c.pouvoir, role, pvSoi, pvAdv),
        onClick: selectionnable ? () => choisirCombattant(c.id) : null,
      })
    );
  });
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirMaintenant(etat);
  const roleHumain = humanRole(etat);
  const roleIa = roleHumain === "j1" ? "j2" : "j1";
  const { combattant_j1: combattantJ1, combattant_j2: combattantJ2 } = etat;

  renderEquipe(elEquipeHumain, etat.joueur_humain.equipe, {
    peutChoisir,
    role: roleHumain,
    pvSoi: etat.joueur_humain.pv,
    pvAdv: etat.joueur_ia.pv,
    combattantJ1,
    combattantJ2,
  });

  renderEquipe(elEquipeIa, etat.joueur_ia.equipe, {
    role: roleIa,
    pvSoi: etat.joueur_ia.pv,
    pvAdv: etat.joueur_humain.pv,
    combattantJ1,
    combattantJ2,
  });
}

async function choisirCombattant(id) {
  const etat = await api("/partie/combattant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ combattant_id: id }),
  });
  render(etat);
}

async function decisionPioche(action) {
  const etat = await api("/partie/pioche", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  render(etat);
}

elBtnPiocher.addEventListener("click", () => decisionPioche("piocher"));
elBtnArreter.addEventListener("click", () => decisionPioche("arreter"));

function renderZoneCentrale(etat) {
  elZonePioche.classList.add("cache");
  elZoneResultat.classList.add("cache");
  elMessageAttente.classList.add("cache");
  vider(elCombattantsEnDuel);

  const humainSlot = humanRole(etat);
  const iaSlot = humainSlot === "j1" ? "j2" : "j1";
  const humainId = etat["combattant_" + humainSlot];
  const iaId = etat["combattant_" + iaSlot];

  const resultat = etat.dernier_resultat;

  [
    { id: humainId, role: "Toi", slot: humainSlot },
    { id: iaId, role: "IA", slot: iaSlot },
  ].forEach(({ id, role, slot }) => {
    const labelRole = `${role} (${slot.toUpperCase()})`;
    if (id === null) {
      const placeholder = document.createElement("div");
      placeholder.className = "carte-duel";
      placeholder.innerHTML = `<div class="role">${labelRole}</div><h3>En attente...</h3>`;
      elCombattantsEnDuel.appendChild(placeholder);
      return;
    }
    const data = trouverCombattant(etat, id);
    const carte = document.createElement("div");
    carte.className = "carte-duel";
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;
    let infoCote = null;
    if (resultat) {
      infoCote = slot === "j1" ? resultat.combattant_j1 : resultat.combattant_j2;
      contenu += `<div class="cartes-jouees" data-cartes-jouees></div>`;
      if (data.pouvoir) {
        contenu += `<div class="pouvoir-actif">Pouvoir : ${data.pouvoir.description}</div>`;
      }
      contenu += `<div class="bloc-stat">
        <span class="valeur-grosse">${resultat.puissance_finale[data.nom]}</span>
        <span class="libelle-stat">Puissance totale</span>
      </div>`;
      contenu += `<ul class="detail-liste">${formaterDetailListe(resultat.detail_puissance[data.nom])}</ul>`;
      if (resultat.gagnants.includes(data.nom)) {
        carte.classList.add("gagnant");
        contenu += `<div class="bloc-stat degats">
          <span class="valeur-grosse petite">${resultat.degats_finale[data.nom]}</span>
          <span class="libelle-stat">Degats infliges</span>
        </div>`;
        contenu += `<ul class="detail-liste degats">${formaterDetailListe(resultat.detail_degats[data.nom])}</ul>`;
      }
    } else {
      contenu += `<div class="cartes-jouees">Puissance ${data.puissance} / Degats ${data.degats}</div>`;
    }
    carte.innerHTML = contenu;

    // Cartes Puissance piochees par ce combattant, affichees visuellement
    // (icone + pastilles) plutot qu'en texte : valable pour le joueur comme
    // pour l'IA, une fois le duel resolu et les cartes reveleés.
    if (infoCote) {
      const zoneCartes = carte.querySelector("[data-cartes-jouees]");
      if (infoCote.cartes.length === 0) {
        zoneCartes.classList.add("cartes-jouees--vide");
        zoneCartes.textContent = "Aucune carte piochee";
      } else {
        infoCote.cartes.forEach((c) => zoneCartes.appendChild(creerCartePuissance(c, { mini: true })));
        if (infoCote.busted) {
          const bust = document.createElement("span");
          bust.className = "badge-bust";
          bust.textContent = "BUST";
          zoneCartes.appendChild(bust);
        }
      }
    }
    elCombattantsEnDuel.appendChild(carte);
  });

  if (etat.phase === "choix_combattant") {
    elMessageAttente.textContent =
      humainId === null ? "Choisis ton Combattant pour ce duel." : "En attente du choix de l'IA...";
    elMessageAttente.classList.remove("cache");
  } else if (etat.phase === "pioche") {
    renderZonePioche(etat, humainSlot, iaSlot);
  } else if (etat.phase === "duel_resolu") {
    elZoneResultat.classList.remove("cache");
    vider(elJournalResolution);
    resultat.log.forEach((ligne) => {
      const p = document.createElement("p");
      if (ligne.includes("remporte le duel")) p.className = "gain";
      p.textContent = ligne;
      elJournalResolution.appendChild(p);
    });
    elBtnDuelSuivant.textContent = etat.terminee ? "Voir le resultat final" : "Duel suivant";
    elBtnDuelSuivant.onclick = etat.terminee ? () => renderFin(etat) : duelSuivant;
  }
}

function renderZonePioche(etat, humainSlot, iaSlot) {
  elZonePioche.classList.remove("cache");

  const infoHumain = etat.pioche[humainSlot];
  const infoIa = etat.pioche[iaSlot];

  elPiocheTasRestant.textContent = `Cartes restantes dans le tas : ${etat.pioche.cartes_restantes_deck}`;

  vider(elMesCartesPiochees);
  if (infoHumain.cartes.length === 0) {
    elMesCartesPiochees.textContent = "Aucune carte piochee pour l'instant.";
  } else {
    infoHumain.cartes.forEach((c) =>
      elMesCartesPiochees.appendChild(c.cachee ? creerCartePuissanceDos() : creerCartePuissance(c))
    );
  }
  elMesTotauxPioche.textContent =
    `Puissance des cartes : +${infoHumain.puissance_cartes} — Malus total : ${infoHumain.malus_total} / ${infoHumain.malus_limite}` +
    (infoHumain.malus_total >= infoHumain.malus_limite ? " (BUST, puissance des cartes annulee)" : "");

  // Les cartes de l'IA restent cachees (contenu inconnu) tant que le duel
  // n'est pas resolu, sauf celles explicitement revelees par un Pouvoir (cf.
  // Oogway/Seigneur skaven) : leur nombre est visible sous forme de dos de
  // cartes, les cartes revelees s'affichent face visible parmi ces dos.
  vider(elIaCartesPiochees);
  const cartesRevelees = infoIa.cartes_revelees || [];
  const premiereRevelee = infoIa.premiere_carte_revelee || null;
  if (infoIa.nb_cartes === 0) {
    elIaCartesPiochees.textContent = "Aucune carte piochee pour l'instant.";
  } else {
    if (premiereRevelee) elIaCartesPiochees.appendChild(creerCartePuissance(premiereRevelee));
    cartesRevelees.forEach((c) => elIaCartesPiochees.appendChild(creerCartePuissance(c)));
    const nbDos = infoIa.nb_cartes - cartesRevelees.length - (premiereRevelee ? 1 : 0);
    for (let i = 0; i < nbDos; i++) elIaCartesPiochees.appendChild(creerCartePuissanceDos());
  }
  elStatutPiocheIa.textContent = infoIa.arrete ? "A passe" : "En train de decider...";

  const monTour = etat.pioche.tour === humainSlot;
  const jePeuxAgir = monTour && !infoHumain.arrete;
  elBtnPiocher.disabled = !jePeuxAgir || etat.pioche.cartes_restantes_deck === 0;
  elBtnArreter.disabled = !jePeuxAgir;
}

async function duelSuivant() {
  const etat = await api("/partie/suivant", { method: "POST" });
  render(etat);
}

function renderFin(etat) {
  ecranPartie.classList.add("cache");
  ecranFin.classList.remove("cache");
  const titre = document.getElementById("titre-fin");
  const detail = document.getElementById("detail-fin");
  if (etat.vainqueur === "humain") titre.textContent = "Victoire !";
  else if (etat.vainqueur === "ia") titre.textContent = "Defaite...";
  else titre.textContent = "Egalite";
  detail.textContent = `Toi : ${etat.joueur_humain.pv} PV — IA : ${etat.joueur_ia.pv} PV`;
}

// ------------------------------------------------------------------- start
initSelectionEcran();
