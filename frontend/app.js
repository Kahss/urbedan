// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

const CARACS = [
  { cle: "force", libelle: "Force", couleur: "rouge", initiale: "F" },
  { cle: "dexterite", libelle: "Dexterite", couleur: "vert", initiale: "D" },
  { cle: "sagesse", libelle: "Sagesse", couleur: "bleu", initiale: "S" },
];

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;

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

function roleHumain(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function roleIa(etat) {
  return etat.j1 === "humain" ? "j2" : "j1";
}

function caracsHtml(data) {
  return CARACS.map(
    (c) =>
      `<span class="carac carac-${c.couleur}" title="${c.libelle}">` +
      `<span class="carac-initiale">${c.initiale}</span><b>${data[c.cle]}</b></span>`
  ).join("");
}

// ------------------------------------------------------------- cartes

function creerCarteCombattant(data, { selectionnable = false, selectionnee = false, active = false, onClick = null } = {}) {
  const carte = document.createElement("div");
  carte.className = "carte-combattant";
  if (selectionnable) carte.classList.add("selectionnable");
  if (selectionnee) carte.classList.add("selectionnee");
  if (active) carte.classList.add("active-duel");
  if (data.utilise) carte.classList.add("utilisee");

  const titre = document.createElement("h4");
  titre.textContent = data.nom;
  carte.appendChild(titre);

  const caracs = document.createElement("div");
  caracs.className = "caracs-combattant";
  caracs.innerHTML = caracsHtml(data);
  carte.appendChild(caracs);

  const stats = document.createElement("div");
  stats.className = "stats-combattant";
  stats.innerHTML = `<span>Degats <b>${data.degats}</b></span><span>Total caracs <b>${data.total_caracs}</b></span>`;
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

function creerDosPioche(pioche, { cliquable = false, onClick = null } = {}) {
  const carte = document.createElement("div");
  carte.className = `carte-bataille dos dos-${pioche.verso || "vide"}`;
  if (cliquable) carte.classList.add("cliquable");
  carte.innerHTML =
    `<span class="dos-marque">?</span>` +
    `<span class="dos-couleur">${pioche.verso || "vide"}</span>` +
    `<span class="dos-restantes">${pioche.restantes} carte${pioche.restantes > 1 ? "s" : ""}</span>`;
  if (cliquable && onClick) carte.addEventListener("click", onClick);
  return carte;
}

function creerCarteRevelee(entree) {
  const el = document.createElement("div");
  el.className = `carte-bataille recto bord-${entree.carte.verso}`;
  const issue = entree.gagnant_nom ? entree.gagnant_nom : "Bataille nulle";
  const classeIssue = entree.gagnant_camp === "humain" ? "gain" : entree.gagnant_camp === "ia" ? "perte" : "nulle";
  el.innerHTML =
    `<span class="revelee-libelle">Derniere carte revelee</span>` +
    `<span class="bataille-nom">${entree.carte.nom}</span>` +
    `<span class="bataille-condition">${entree.carte.condition}</span>` +
    `<span class="revelee-issue ${classeIssue}">${issue}</span>`;
  return el;
}

function marqueursBatailles(gagnees, total) {
  let html = "";
  for (let i = 0; i < total; i++) {
    html += `<span class="marqueur ${i < gagnees ? "gagne" : ""}"></span>`;
  }
  return html;
}

// ------------------------------------------------------- ecran de selection

async function initSelectionEcran() {
  combattantsDisponibles = await api("/combattants");
  equipeSelectionnee.clear();
  renderGrilleSelection();
  renderLegendeDeck(await api("/batailles"));
}

function renderLegendeDeck(cartes) {
  const liste = document.getElementById("legende-deck-liste");
  vider(liste);
  cartes.forEach((carte) => {
    const el = document.createElement("div");
    el.className = `legende-carte bord-${carte.verso}`;
    el.innerHTML =
      `<span class="legende-nom">${carte.nom}</span>` +
      `<span class="legende-condition">${carte.condition}</span>` +
      `<span class="legende-verso puce-${carte.verso}">dos ${carte.verso}</span>`;
    liste.appendChild(el);
  });
}

function renderGrilleSelection() {
  const grille = document.getElementById("grille-selection");
  vider(grille);
  combattantsDisponibles.forEach((c) => {
    grille.appendChild(
      creerCarteCombattant(
        { ...c, utilise: false },
        {
          selectionnable: true,
          selectionnee: equipeSelectionnee.has(c.id),
          onClick: () => toggleSelection(c.id),
        }
      )
    );
  });
  document.getElementById("compteur-selection").textContent = `${equipeSelectionnee.size} / 4 selectionnes`;
  document.getElementById("btn-lancer-partie").disabled = equipeSelectionnee.size !== 4;
}

function toggleSelection(id) {
  if (equipeSelectionnee.has(id)) {
    equipeSelectionnee.delete(id);
  } else if (equipeSelectionnee.size < 4) {
    equipeSelectionnee.add(id);
  }
  renderGrilleSelection();
}

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

function peutChoisirCombattant(etat) {
  return etat.phase === "choix_combattant" && etat["combattant_" + roleHumain(etat)] === null;
}

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderCartesDeck(etat);
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
  document.getElementById("pv-humain-texte").textContent = `${etat.joueur_humain.pv} PV`;
  document.getElementById("pv-ia-texte").textContent = `${etat.joueur_ia.pv} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(etat.joueur_humain.pv);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(etat.joueur_ia.pv);
  document.getElementById("duel-numero-texte").textContent =
    `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
  document.getElementById("premier-joueur-texte").textContent =
    etat.j1 === "humain" ? "Tu es J1 : tu engages et tu pioches en premier" : "L'IA est J1 : elle engage et pioche en premier";
}

function renderCartesDeck(etat) {
  const conteneur = document.getElementById("cartes-deck-liste");
  vider(conteneur);
  (etat.cartes_du_deck || []).forEach((carte) => {
    const el = document.createElement("div");
    el.className = `mini-bataille puce-${carte.verso}`;
    if (!carte.en_pioche) el.classList.add("sortie");
    el.title = `${carte.nom} - ${carte.condition} (dos ${carte.verso})`;
    el.textContent = carte.nom;
    conteneur.appendChild(el);
  });
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirCombattant(etat);

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable: peutChoisir && !c.utilise,
        active,
        onClick: peutChoisir && !c.utilise ? () => soumettreCombattant(c.id) : null,
      })
    );
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleIa.appendChild(creerCarteCombattant(c, { active }));
  });
}

async function soumettreCombattant(id) {
  const etat = await api("/partie/combattant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ combattant_id: id }),
  });
  render(etat);
}

async function soumettrePioche(index) {
  const etat = await api("/partie/bataille", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pioche: index }),
  });
  render(etat);
}

function renderZoneCentrale(etat) {
  const zonePioches = document.getElementById("zone-pioches");
  const zoneJournal = document.getElementById("zone-journal");
  const zoneResultat = document.getElementById("zone-resultat");
  const messageAttente = document.getElementById("message-attente");
  const conteneurDuel = document.getElementById("combattants-en-duel");

  zonePioches.classList.add("cache");
  zoneJournal.classList.add("cache");
  zoneResultat.classList.add("cache");
  messageAttente.classList.add("cache");
  vider(conteneurDuel);

  const slotHumain = roleHumain(etat);
  const slotIa = roleIa(etat);
  const resultat = etat.dernier_resultat;

  [
    { role: "Toi", slot: slotHumain },
    { role: "IA", slot: slotIa },
  ].forEach(({ role, slot }) => {
    const id = etat["combattant_" + slot];
    const carte = document.createElement("div");
    carte.className = "carte-duel";
    const labelRole = `${role} (${slot.toUpperCase()})`;
    if (id === null) {
      carte.innerHTML = `<div class="role">${labelRole}</div><h3>En attente...</h3>`;
      conteneurDuel.appendChild(carte);
      return;
    }
    const data = trouverCombattant(etat, id);
    const gagnees = etat.score[slot];
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;
    contenu += `<div class="caracs-combattant grand">${caracsHtml(data)}</div>`;
    contenu += `<div class="marqueurs">${marqueursBatailles(gagnees, etat.batailles_pour_gagner)}</div>`;
    contenu += `<div class="compte-batailles">${gagnees} bataille${gagnees > 1 ? "s" : ""} remportee${gagnees > 1 ? "s" : ""}</div>`;
    if (resultat) {
      if (resultat.gagnants_roles.includes(slot)) {
        carte.classList.add("gagnant");
        contenu += `<div class="bloc-stat degats"><span class="valeur-grosse petite">${resultat.degats[data.nom]}</span>` +
          `<span class="libelle-stat">Degats infliges</span></div>`;
      } else {
        contenu += `<div class="bloc-stat"><span class="libelle-stat">Duel perdu</span></div>`;
      }
    } else {
      contenu += `<div class="degats-annonce">Degats : <b>${data.degats}</b></div>`;
    }
    carte.innerHTML = contenu;
    conteneurDuel.appendChild(carte);
  });

  // Journal des batailles du duel en cours
  if ((etat.journal_batailles || []).length) {
    zoneJournal.classList.remove("cache");
    const journal = document.getElementById("journal-batailles");
    vider(journal);
    etat.journal_batailles.forEach((entree) => {
      const ligne = document.createElement("div");
      ligne.className = "ligne-bataille";
      if (entree.gagnant_camp === "humain") ligne.classList.add("gain");
      else if (entree.gagnant_camp === "ia") ligne.classList.add("perte");
      else ligne.classList.add("nulle");
      const valeurs = ["j1", "j2"]
        .map((slot) => {
          const nom = trouverCombattant(etat, etat["combattant_" + slot]).nom;
          const detail = entree.valeurs[slot].map(([libelle, valeur]) => `${libelle} ${valeur}`).join(" + ");
          return `<span class="bataille-valeurs">${nom} : ${detail}</span>`;
        })
        .join(`<span class="contre">vs</span>`);
      const issue = entree.gagnant_nom
        ? `${entree.gagnant_nom} remporte la bataille`
        : "Bataille nulle";
      ligne.innerHTML =
        `<span class="bataille-numero">${entree.numero}</span>` +
        `<span class="puce-${entree.carte.verso}" title="dos ${entree.carte.verso}"></span>` +
        `<span class="bataille-titre">${entree.carte.nom}<em>${entree.carte.condition}</em></span>` +
        `<span class="bataille-detail">${valeurs}</span>` +
        `<span class="bataille-issue">${issue}</span>` +
        `<span class="bataille-source">pioche ${entree.pioche} (${entree.choisie_par === "humain" ? "toi" : "IA"})</span>`;
      journal.appendChild(ligne);
    });
  }

  if (etat.phase === "choix_combattant") {
    messageAttente.classList.remove("cache");
    messageAttente.textContent = peutChoisirCombattant(etat)
      ? slotHumain === "j1"
        ? "Tu es J1 : engage ton Combattant, l'IA choisira le sien en le connaissant."
        : "Tu es J2 : engage ton Combattant en connaissant celui que l'IA vient d'engager."
      : "En attente du choix de l'IA...";
  } else if (etat.phase === "batailles") {
    zonePioches.classList.remove("cache");
    const conteneurPioches = document.getElementById("pioches");
    vider(conteneurPioches);
    const aMoi = etat.joueur_actif === "humain";
    document.getElementById("libelle-pioches").textContent = aMoi
      ? "A toi : choisis la pioche dont tu veux reveler la carte du dessus."
      : "L'IA choisit sa pioche...";
    const derniere = (etat.journal_batailles || []).slice(-1)[0];
    etat.pioches.forEach((pioche, rang) => {
      // La derniere carte revelee est posee entre les deux pioches, face visible.
      if (rang === 1 && derniere) conteneurPioches.appendChild(creerCarteRevelee(derniere));
      conteneurPioches.appendChild(
        creerDosPioche(pioche, {
          cliquable: aMoi && pioche.restantes > 0,
          onClick: () => soumettrePioche(pioche.index),
        })
      );
    });
  } else if (etat.phase === "duel_resolu") {
    zoneResultat.classList.remove("cache");
    const journal = document.getElementById("journal-resolution");
    vider(journal);
    const humainGagne = resultat.gagnants_roles.includes(slotHumain);
    const iaGagne = resultat.gagnants_roles.includes(slotIa);
    const titre = document.createElement("p");
    titre.className = humainGagne && !iaGagne ? "gain" : iaGagne && !humainGagne ? "perte" : "";
    titre.textContent =
      `Duel ${resultat.duel_numero} : ${resultat.score[slotHumain]}-${resultat.score[slotIa]}` +
      (resultat.par_plafond ? ` (plafond de ${etat.cartes_max_par_duel} cartes atteint)` : "") +
      ` - ${resultat.gagnants.join(" et ")} remporte${resultat.gagnants.length > 1 ? "nt" : ""} le duel`;
    journal.appendChild(titre);
    Object.entries(resultat.degats).forEach(([nom, valeur]) => {
      const p = document.createElement("p");
      p.textContent = `${nom} inflige ${valeur} Degats`;
      journal.appendChild(p);
    });
    const btn = document.getElementById("btn-duel-suivant");
    btn.textContent = etat.terminee ? "Voir le resultat final" : "Duel suivant";
    btn.onclick = etat.terminee ? () => renderFin(etat) : duelSuivant;
  }
}

async function duelSuivant() {
  const etat = await api("/partie/suivant", { method: "POST" });
  render(etat);
}

function renderFin(etat) {
  ecranPartie.classList.add("cache");
  ecranFin.classList.remove("cache");
  const titre = document.getElementById("titre-fin");
  if (etat.vainqueur === "humain") titre.textContent = "Victoire !";
  else if (etat.vainqueur === "ia") titre.textContent = "Defaite...";
  else titre.textContent = "Egalite";
  document.getElementById("detail-fin").textContent =
    `Toi : ${etat.joueur_humain.pv} PV — IA : ${etat.joueur_ia.pv} PV`;
}

// ------------------------------------------------------------------- start
initSelectionEcran();
