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

// Un seul appel a l'API peut faire jouer plusieurs batailles (celle du joueur, puis celle
// de l'IA) : on les rejoue une par une, animation comprise, avant d'afficher l'etat final.
const DUREE_BATAILLE = 1100;
let bataillesAffichees = 0;

function attendre(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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

function creerCarteRevelee(entree, { animee = false } = {}) {
  const el = document.createElement("div");
  el.className = `carte-bataille recto bord-${entree.carte.verso}`;
  const issue = entree.gagnant_nom ? entree.gagnant_nom : "Bataille nulle";
  const classeIssue = entree.gagnant_camp === "humain" ? "gain" : entree.gagnant_camp === "ia" ? "perte" : "nulle";
  if (animee) {
    // Deux temps : la carte sort de la pioche choisie, puis file vers le camp qui
    // remporte la bataille (ou grise sur place si la bataille est nulle).
    el.classList.add("animee", `depuis-pioche-${entree.pioche}`, `attribution-${classeIssue}`);
  }
  el.innerHTML =
    `<span class="revelee-libelle">Bataille ${entree.numero}</span>` +
    `<span class="bataille-nom">${entree.carte.nom}</span>` +
    `<span class="bataille-condition">${entree.carte.condition}</span>` +
    `<span class="revelee-issue ${classeIssue}">${issue}</span>`;
  return el;
}

function marqueursBatailles(gagnees, total, { dernierAnime = false } = {}) {
  let html = "";
  for (let i = 0; i < total; i++) {
    const classes = [i < gagnees ? "gagne" : ""];
    if (dernierAnime && i === gagnees - 1) classes.push("vient-de-gagner");
    html += `<span class="marqueur ${classes.join(" ")}"></span>`;
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
  bataillesAffichees = 0;
  await appliquerEtat(etat);
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

async function appliquerEtat(etat) {
  const journal = etat.journal_batailles || [];
  if (journal.length < bataillesAffichees) bataillesAffichees = 0;  // nouveau duel
  while (bataillesAffichees < journal.length) {
    bataillesAffichees += 1;
    render(etat, { jusqua: bataillesAffichees, animation: true });
    await attendre(DUREE_BATAILLE);
  }
  bataillesAffichees = journal.length;
  render(etat);
}

function render(etat, options = {}) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat, options);
  renderEquipes(etat, options);
  renderZoneCentrale(etat, options);
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

function pvAffiches(etat, enAnimation) {
  const pv = { humain: etat.joueur_humain.pv, ia: etat.joueur_ia.pv };
  const resultat = etat.dernier_resultat;
  // Tant que les batailles defilent, le duel n'est pas encore cense etre resolu : on
  // rend les PV perdus par le camp qui vient de subir les Degats, pour ne pas devoiler
  // l'issue du duel avant la derniere bataille.
  if (enAnimation && resultat) {
    resultat.gagnants_roles.forEach((role) => {
      const gagnant = resultat["combattant_" + role];
      const perdant = resultat["combattant_" + (role === "j1" ? "j2" : "j1")];
      pv[perdant.camp] += resultat.degats[gagnant.nom];
    });
  }
  return pv;
}

function renderTableauBord(etat, options = {}) {
  const pv = pvAffiches(etat, options.animation === true);
  document.getElementById("pv-humain-texte").textContent = `${pv.humain} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pv.ia} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(pv.humain);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(pv.ia);
  document.getElementById("duel-numero-texte").textContent =
    `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
  document.getElementById("premier-joueur-texte").textContent =
    etat.j1 === "humain" ? "Tu es J1 : tu engages et tu pioches en premier" : "L'IA est J1 : elle engage et pioche en premier";
}

function renderEquipes(etat, options = {}) {
  const peutChoisir = peutChoisirCombattant(etat);
  // Pendant l'animation, les deux Combattants engages sont encore en duel : le moteur les
  // a deja marques "utilise", mais l'interface ne doit pas le montrer avant la fin.
  const enDuel = (c) =>
    options.animation === true && (c.id === etat.combattant_j1 || c.id === etat.combattant_j2)
      ? { ...c, utilise: false }
      : c;

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((brut) => {
    const c = enDuel(brut);
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
  etat.joueur_ia.equipe.forEach((brut) => {
    const c = enDuel(brut);
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
  await appliquerEtat(etat);
}

async function soumettrePioche(index) {
  const etat = await api("/partie/bataille", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pioche: index }),
  });
  await appliquerEtat(etat);
}

function renderZoneCentrale(etat, options = {}) {
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

  // Pendant l'animation, on rejoue l'etat tel qu'il etait apres la bataille `jusqua` :
  // score, journal et pioches sont reconstitues a cet instant, et le resultat du duel
  // reste masque jusqu'a la derniere bataille.
  const enAnimation = options.animation === true;
  const journalComplet = etat.journal_batailles || [];
  const jusqua = options.jusqua === undefined ? journalComplet.length : options.jusqua;
  const entrees = journalComplet.slice(0, jusqua);
  const enAttente = journalComplet.slice(jusqua);
  const derniere = entrees[entrees.length - 1];
  const phase = enAnimation ? "batailles" : etat.phase;
  const resultat = enAnimation ? null : etat.dernier_resultat;
  const score = {
    j1: entrees.filter((e) => e.gagnant_role === "j1").length,
    j2: entrees.filter((e) => e.gagnant_role === "j2").length,
  };

  const slotHumain = roleHumain(etat);
  const slotIa = roleIa(etat);

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
    const gagnees = score[slot];
    const vientDeGagner = enAnimation && derniere && derniere.gagnant_role === slot;
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;
    contenu += `<div class="caracs-combattant grand">${caracsHtml(data)}</div>`;
    contenu += `<div class="marqueurs">${marqueursBatailles(gagnees, etat.batailles_pour_gagner, { dernierAnime: vientDeGagner })}</div>`;
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

  // Journal des batailles deja resolues
  if (entrees.length) {
    zoneJournal.classList.remove("cache");
    const journal = document.getElementById("journal-batailles");
    vider(journal);
    entrees.forEach((entree, rang) => {
      const ligne = document.createElement("div");
      ligne.className = "ligne-bataille";
      if (entree.gagnant_camp === "humain") ligne.classList.add("gain");
      else if (entree.gagnant_camp === "ia") ligne.classList.add("perte");
      else ligne.classList.add("nulle");
      if (enAnimation && rang === entrees.length - 1) ligne.classList.add("nouvelle");
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
        `<span class="bataille-issue">${issue}</span>`;
      journal.appendChild(ligne);
    });
  }

  if (phase === "choix_combattant") {
    messageAttente.classList.remove("cache");
    messageAttente.textContent = peutChoisirCombattant(etat)
      ? slotHumain === "j1"
        ? "Tu es J1 : engage ton Combattant, l'IA choisira le sien en le connaissant."
        : "Tu es J2 : engage ton Combattant en connaissant celui que l'IA vient d'engager."
      : "En attente du choix de l'IA...";
  } else if (phase === "batailles") {
    zonePioches.classList.remove("cache");
    const conteneurPioches = document.getElementById("pioches");
    vider(conteneurPioches);
    const aMoi = etat.joueur_actif === "humain" && !enAnimation && !enAttente.length;
    document.getElementById("libelle-pioches").textContent = enAnimation
      ? `Bataille ${derniere.numero} : ${derniere.carte.condition}`
      : aMoi
        ? "A toi : choisis la pioche dont tu veux reveler la carte du dessus."
        : "L'IA choisit sa pioche...";
    etat.pioches.forEach((pioche, rang) => {
      // La derniere carte revelee est posee entre les deux pioches, face visible.
      if (rang === 1 && derniere) {
        conteneurPioches.appendChild(creerCarteRevelee(derniere, { animee: enAnimation }));
      }
      // Etat de la pioche a l'instant reconstitue : les cartes tirees plus tard y dorment
      // encore, et son dos est celui que le joueur voyait alors.
      const aVenir = enAttente.find((e) => e.pioche === pioche.index + 1);
      conteneurPioches.appendChild(
        creerDosPioche(
          {
            index: pioche.index,
            verso: aVenir ? aVenir.carte.verso : pioche.verso,
            restantes: pioche.restantes + enAttente.filter((e) => e.pioche === pioche.index + 1).length,
          },
          { cliquable: aMoi && pioche.restantes > 0, onClick: () => soumettrePioche(pioche.index) }
        )
      );
    });
  } else if (phase === "duel_resolu") {
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
  bataillesAffichees = 0;
  await appliquerEtat(etat);
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
