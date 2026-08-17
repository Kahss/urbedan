// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

const ZONES = ["Bitume", "Hauteur", "Souterrain"];

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;
let legendeChargee = false;

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

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
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

function rondsEnergie(energie) {
  return Array.from({ length: energie }, () => `<span class="rond-energie"></span>`).join("");
}

function seuilEnergieInfo(energieMin) {
  if (energieMin > 0) {
    return { html: rondsEnergie(energieMin), titre: `Energie ${energieMin} ou plus` };
  }
  return { html: `<span class="rond-energie rond-energie-vide"></span>`, titre: "Toujours actif" };
}

// ------------------------------------------------------------ Avantage

// Les 3 Zones du champ de bataille, celles de l'Avantage du Combattant mises en avant.
// Quand le dos de la carte du duel est connu, chaque Zone prend sa couleur : le joueur lit
// d'un coup d'oeil si le Combattant couvre les bonnes cases.
function creerAvantage(avantage, dos, { compact = false } = {}) {
  const el = document.createElement("div");
  el.className = compact ? "avantage compact" : "avantage";
  const zones = avantage || [];
  el.title = "Avantage : " + zones.map((z) => ZONES[z - 1]).join(", ");
  for (let zone = 1; zone <= 3; zone++) {
    const cellule = document.createElement("span");
    const couvert = zones.includes(zone);
    cellule.className = "avantage-case " + (couvert ? "couvert" : "hors");
    if (dos) cellule.classList.add("dos-" + dos[zone - 1]);
    cellule.textContent = ZONES[zone - 1][0];
    el.appendChild(cellule);
  }
  return el;
}

function creerCarteCombattant(data, options = {}) {
  const {
    selectionnable = false, selectionnee = false, active = false,
    conditionValidee = false, dos = null, onClick = null,
  } = options;
  const carte = document.createElement("div");
  carte.className = "carte-combattant";
  if (selectionnable) carte.classList.add("selectionnable");
  if (selectionnee) carte.classList.add("selectionnee");
  if (active) carte.classList.add("active-duel");
  if (conditionValidee) carte.classList.add("condition-validee");
  if (data.utilise) carte.classList.add("utilisee");

  const titre = document.createElement("h4");
  titre.textContent = data.nom;
  carte.appendChild(titre);

  const stats = document.createElement("div");
  stats.className = "stats-combattant";
  stats.innerHTML = `<span>Puissance <b>${data.puissance}</b></span><span>Degats <b>${data.degats}</b></span>`;
  carte.appendChild(stats);

  carte.appendChild(creerAvantage(data.avantage, dos));

  const liste = document.createElement("ul");
  liste.className = "liste-pouvoirs";
  if (data.pouvoir) {
    const li = document.createElement("li");
    const seuil = seuilEnergieInfo(data.pouvoir.energie_min);
    li.innerHTML = `<span class="num" title="${seuil.titre}">${seuil.html}</span>${data.pouvoir.description}`;
    liste.appendChild(li);
  }
  carte.appendChild(liste);

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

// ------------------------------------------------------ champ de bataille

// Tant que le duel n'est pas resolu, le serveur ne transmet que `dos` : les valeurs et
// l'Energie n'existent pas cote client, il n'y a donc rien a devoiler par inadvertance.
function creerChampCarte(champ) {
  const carte = document.createElement("div");
  carte.className = "champ-carte-interne" + (champ.revele ? " revele" : " cache-recto");

  const titre = document.createElement("div");
  titre.className = "champ-titre";
  titre.textContent = champ.revele ? champ.nom : "Champ de bataille — face cachee";
  carte.appendChild(titre);

  const cases = document.createElement("div");
  cases.className = "champ-cases";
  for (let i = 0; i < 3; i++) {
    const couleur = champ.revele ? champ.cases[i].couleur : champ.dos[i];
    const bloc = document.createElement("div");
    bloc.className = `champ-case dos-${couleur}`;
    const zone = `<span class="champ-zone">${ZONES[i]}</span>`;
    if (champ.revele) {
      const valeur = champ.cases[i].valeur;
      bloc.innerHTML = `${zone}
        <span class="champ-valeur">${valeur > 0 ? "+" : ""}${valeur}</span>
        <span class="champ-energie">${rondsEnergie(champ.cases[i].energie)}</span>`;
    } else {
      bloc.innerHTML = `${zone}<span class="champ-valeur inconnu">?</span><span class="champ-energie"></span>`;
    }
    cases.appendChild(bloc);
  }
  carte.appendChild(cases);
  return carte;
}

async function remplirLegendeChamps() {
  if (legendeChargee) return;
  const modeles = await api("/champs");
  const conteneur = document.getElementById("legende-champs-liste");
  vider(conteneur);
  modeles.forEach((modele) => {
    const el = document.createElement("div");
    el.className = "legende-modele";
    const cases = modele.cases
      .map(
        (c) =>
          `<span class="legende-case dos-${c.couleur}">${c.valeur > 0 ? "+" : ""}${c.valeur}` +
          `<span class="champ-energie">${rondsEnergie(c.energie)}</span></span>`
      )
      .join("");
    el.innerHTML = `<span class="legende-nom">${modele.nom}</span><span class="legende-cases">${cases}</span>` +
      `<span class="legende-exemplaires">x${modele.exemplaires}</span>`;
    conteneur.appendChild(el);
  });
  legendeChargee = true;
}

// ------------------------------------------------------- ecran de selection

async function initSelectionEcran() {
  combattantsDisponibles = await api("/combattants");
  equipeSelectionnee.clear();
  renderGrilleSelection();
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
  const compteur = document.getElementById("compteur-selection");
  compteur.textContent = `${equipeSelectionnee.size} / 4 selectionnes`;
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
  remplirLegendeChamps();
  render(etat);
});

document.getElementById("btn-nouvelle-partie").addEventListener("click", async () => {
  ecranFin.classList.add("cache");
  ecranSelection.classList.remove("cache");
  await initSelectionEcran();
});

// ------------------------------------------------------------- ecran partie

function peutChoisirMaintenant(etat) {
  return etat.phase === "choix_combattant" && etat["combattant_" + humanRole(etat)] === null;
}

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderChamp(etat);
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
  document.getElementById("pv-humain-texte").textContent = `${pvH} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pvI} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(pvH);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(pvI);
  document.getElementById("duel-numero-texte").textContent =
    `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function renderChamp(etat) {
  const conteneur = document.getElementById("champ-carte");
  vider(conteneur);
  conteneur.appendChild(creerChampCarte(etat.champ));

  const consigne = document.getElementById("champ-consigne");
  if (etat.phase === "duel_resolu") {
    consigne.textContent = "Champ de bataille revele : chaque Combattant encaisse ses Zones.";
  } else if (peutChoisirMaintenant(etat)) {
    consigne.textContent =
      "Seules les couleurs sont connues : vert = valeur positive, gris = nulle, rouge = negative. " +
      "Ni les valeurs exactes, ni l'Energie ne sont visibles avant la revelation.";
  } else {
    consigne.textContent = "En attente de l'adversaire...";
  }
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirMaintenant(etat);
  const roleHumain = humanRole(etat);
  const roleIa = roleHumain === "j1" ? "j2" : "j1";
  const dos = etat.champ.dos;

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable: peutChoisir && !c.utilise,
        active,
        dos,
        conditionValidee: conditionEstValidee(c.pouvoir, roleHumain, etat.joueur_humain.pv, etat.joueur_ia.pv),
        onClick: peutChoisir && !c.utilise ? () => engager(c.id) : null,
      })
    );
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleIa.appendChild(
      creerCarteCombattant(c, {
        active,
        dos,
        conditionValidee: conditionEstValidee(c.pouvoir, roleIa, etat.joueur_ia.pv, etat.joueur_humain.pv),
      })
    );
  });
}

async function engager(combattantId) {
  const etat = await api("/partie/combattant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ combattant_id: combattantId }),
  });
  render(etat);
}

function renderZoneCentrale(etat) {
  const zoneResultat = document.getElementById("zone-resultat");
  const messageAttente = document.getElementById("message-attente");
  const conteneurDuel = document.getElementById("combattants-en-duel");

  zoneResultat.classList.add("cache");
  messageAttente.classList.add("cache");
  vider(conteneurDuel);

  const humainSlot = humanRole(etat);
  const iaSlot = humainSlot === "j1" ? "j2" : "j1";
  const resultat = etat.dernier_resultat;

  [
    { id: etat["combattant_" + humainSlot], role: "Toi", slot: humainSlot },
    { id: etat["combattant_" + iaSlot], role: "IA", slot: iaSlot },
  ].forEach(({ id, role, slot }) => {
    const labelRole = `${role} (${slot.toUpperCase()})`;
    if (id === null) {
      const placeholder = document.createElement("div");
      placeholder.className = "carte-duel";
      placeholder.innerHTML = `<div class="role">${labelRole}</div><h3>En attente...</h3>`;
      conteneurDuel.appendChild(placeholder);
      return;
    }
    const data = trouverCombattant(etat, id);
    const carte = document.createElement("div");
    carte.className = "carte-duel";
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;

    if (resultat) {
      const infoCote = resultat.combattant_j1.nom === data.nom ? resultat.combattant_j1 : resultat.combattant_j2;
      contenu += `<div class="recolte">
        <span class="recolte-bonus">${infoCote.bonus_champ >= 0 ? "+" : ""}${infoCote.bonus_champ}</span>
        <span class="recolte-energie">${rondsEnergie(infoCote.energie) || "&mdash;"}</span>
      </div>`;
      const pouvoirActif = data.pouvoir && infoCote.energie >= data.pouvoir.energie_min ? data.pouvoir : null;
      contenu += `<div class="pouvoir-actif">${
        pouvoirActif
          ? `Pouvoir actif : ${pouvoirActif.description}`
          : "Pouvoir non active (Energie insuffisante)"
      }</div>`;
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
      contenu += `<div class="recolte-attente">Puissance ${data.puissance} / Degats ${data.degats}</div>`;
    }
    carte.innerHTML = contenu;
    carte.appendChild(creerAvantage(data.avantage, etat.champ.dos, { compact: true }));
    conteneurDuel.appendChild(carte);
  });

  if (etat.phase === "choix_combattant") {
    messageAttente.textContent = peutChoisirMaintenant(etat)
      ? "Engage le Combattant qui tire le meilleur parti de ce champ de bataille."
      : "En attente du choix de l'IA...";
    messageAttente.classList.remove("cache");
  } else if (etat.phase === "duel_resolu") {
    zoneResultat.classList.remove("cache");
    const journal = document.getElementById("journal-resolution");
    vider(journal);
    resultat.log.forEach((ligne) => {
      const p = document.createElement("p");
      if (ligne.includes("remporte le duel")) p.className = "gain";
      p.textContent = ligne;
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
  const detail = document.getElementById("detail-fin");
  if (etat.vainqueur === "humain") titre.textContent = "Victoire !";
  else if (etat.vainqueur === "ia") titre.textContent = "Defaite...";
  else titre.textContent = "Egalite";
  detail.textContent = `Toi : ${etat.joueur_humain.pv} PV — IA : ${etat.joueur_ia.pv} PV`;
}

// ------------------------------------------------------------------- start
initSelectionEcran();
