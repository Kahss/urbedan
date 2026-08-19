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

// `effectives` (facultatif) donne les caracteristiques du duel en cours : une capacite
// adverse peut en avoir ramene une a 0, la valeur imprimee est alors barree.
function caracsHtml(data, effectives) {
  return CARACS.map((c) => {
    const base = data[c.cle];
    const valeur = effectives ? effectives[c.cle] : base;
    const annulee = valeur !== base;
    const titre = annulee ? `${c.libelle} annulee (${base} sur la carte)` : c.libelle;
    return (
      `<span class="carac carac-${c.couleur}${annulee ? " annulee" : ""}" title="${titre}">` +
      `<span class="carac-initiale">${c.initiale}</span><b>${valeur}</b>` +
      (annulee ? `<s>${base}</s>` : "") +
      `</span>`
    );
  }).join("");
}

// Capacite d'un Combattant. `statut` ("active", "inactive", "en_attente") n'est connu que
// pendant un duel : sur l'ecran de selection, la capacite est simplement decrite.
function capaciteHtml(capacite, statut) {
  if (!capacite) return "";
  const classes = ["capacite"];
  if (statut) classes.push("statut-" + statut);
  const etiquettes = { active: "active", inactive: "inactive", en_attente: "selon l'issue" };
  const marque = statut ? `<span class="capacite-statut">${etiquettes[statut]}</span>` : "";
  return (
    `<div class="${classes.join(" ")}"><span class="capacite-etiquette">Capacite</span>` +
    `<span class="capacite-texte">${capacite.libelle}</span>${marque}</div>`
  );
}

// ------------------------------------------------------------- cartes

function creerCarteCombattant(data, { selectionnable = false, selectionnee = false, active = false, onClick = null, statutCapacite = null } = {}) {
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

  if (data.capacite) {
    const capacite = document.createElement("div");
    capacite.innerHTML = capaciteHtml(data.capacite, statutCapacite);
    carte.appendChild(capacite.firstChild);
  }

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
  renderLegendeCapacites(await api("/capacites"));
}

function renderLegendeCapacites(vocabulaire) {
  const liste = document.getElementById("legende-capacites-liste");
  vider(liste);
  [
    { titre: "Condition (facultative) — quand la Capacite s'active", cle: "conditions" },
    { titre: "Effet (obligatoire) — ce qu'elle fait", cle: "effets" },
    { titre: "Multiplicateur (facultatif) — combien de fois l'effet s'applique", cle: "multiplicateurs" },
  ].forEach(({ titre, cle }) => {
    const bloc = document.createElement("div");
    bloc.className = "legende-capacite-bloc";
    const lignes = vocabulaire[cle]
      .map((item) => `<li><b>${item.libelle || item.cle}</b> : ${item.texte}</li>`)
      .join("");
    bloc.innerHTML = `<h5>${titre}</h5><ul>${lignes}</ul>`;
    liste.appendChild(bloc);
  });
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

document.getElementById("btn-equipe-aleatoire").addEventListener("click", () => {
  // Tire 4 Combattants au hasard parmi tous ceux du roster, en remplacant la selection.
  const melange = combattantsDisponibles.slice();
  for (let i = melange.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [melange[i], melange[j]] = [melange[j], melange[i]];
  }
  equipeSelectionnee.clear();
  melange.slice(0, 4).forEach((c) => equipeSelectionnee.add(c.id));
  renderGrilleSelection();
});

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
  const resultat = etat.dernier_resultat;
  // Tant que les batailles defilent, le duel n'est pas encore cense etre resolu : on
  // reaffiche les PV tels qu'ils etaient avant les Degats et les effets de Capacite du
  // duel, pour ne pas devoiler son issue avant la derniere bataille.
  if (enAnimation && resultat) {
    return { ...resultat.pv_debut };
  }
  return { humain: etat.joueur_humain.pv, ia: etat.joueur_ia.pv };
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

// Le slot ("j1" / "j2") occupe par ce Combattant dans le duel en cours, s'il y combat.
function slotDuel(etat, id) {
  if (etat.combattant_j1 === id) return "j1";
  if (etat.combattant_j2 === id) return "j2";
  return null;
}

function statutCapacite(etat, id) {
  const slot = slotDuel(etat, id);
  if (!slot) return null;
  const capacite = (etat.capacites_duel || {})[slot];
  return capacite ? capacite.statut : null;
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
        statutCapacite: active ? statutCapacite(etat, c.id) : null,
        onClick: peutChoisir && !c.utilise ? () => soumettreCombattant(c.id) : null,
      })
    );
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((brut) => {
    const c = enDuel(brut);
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleIa.appendChild(
      creerCarteCombattant(c, { active, statutCapacite: active ? statutCapacite(etat, c.id) : null })
    );
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
  const bandeauCapacites = document.getElementById("capacites-duel");

  zonePioches.classList.add("cache");
  zoneJournal.classList.add("cache");
  zoneResultat.classList.add("cache");
  messageAttente.classList.add("cache");
  bandeauCapacites.classList.add("cache");
  vider(conteneurDuel);
  vider(bandeauCapacites);

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
    // Caracteristiques du duel : une capacite adverse peut en avoir ramene une a 0.
    const caracsDuel = (etat.caracs_duel || {})[slot];
    const capacite = resultat
      ? resultat["combattant_" + slot].capacite
      : (etat.capacites_duel || {})[slot];
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;
    contenu += `<div class="caracs-combattant grand">${caracsHtml(data, caracsDuel)}</div>`;
    contenu += capaciteHtml(capacite, capacite ? capacite.statut : null);
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

  // Capacites qui agissent pendant les batailles (Initiative, annulation de couleur) :
  // elles sont connues des l'engagement des deux Combattants, donc affichables sans
  // rien devoiler de l'issue du duel.
  const passives = etat.capacites_passives || [];
  if (passives.length && phase !== "choix_combattant") {
    bandeauCapacites.classList.remove("cache");
    passives.forEach((entree) => {
      const ligne = document.createElement("div");
      ligne.className = "ligne-capacite" + (entree.camp ? ` ${entree.camp}` : "");
      ligne.innerHTML =
        `<span class="capacite-etiquette">Capacite</span><span>${entree.texte}</span>`;
      bandeauCapacites.appendChild(ligne);
    });
  }

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
        ? `${entree.gagnant_nom} remporte la bataille` +
          (entree.par_initiative ? " <em>(Initiative)</em>" : "")
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
    (resultat.capacites || []).forEach((entree) => {
      const p = document.createElement("p");
      p.className = "ligne-capacite-resultat";
      p.innerHTML = `<span class="capacite-etiquette">Capacite</span>${entree.texte}`;
      journal.appendChild(p);
    });
    Object.entries(resultat.degats).forEach(([nom, valeur]) => {
      const p = document.createElement("p");
      p.textContent = `${nom} inflige ${valeur} Degats`;
      journal.appendChild(p);
    });
    ["humain", "ia"].forEach((camp) => {
      const variation = (resultat.effets_pv || {})[camp];
      if (!variation) return;
      const p = document.createElement("p");
      p.className = camp === "humain" ? (variation > 0 ? "gain" : "perte") : variation > 0 ? "perte" : "gain";
      p.textContent =
        `${camp === "humain" ? "Toi" : "L'IA"} : ${variation > 0 ? "+" : ""}${variation} PV (Capacite)`;
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
