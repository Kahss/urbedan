// Urban Eredan, version duo - logique frontend (vanilla JS, jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;
let duoSelectionne = [];
let ciblagesEnCours = {};

// -------------------------------------------------------------- utilitaires

async function api(path, options) {
  const reponse = await fetch(API + path, options);
  const data = await reponse.json();
  if (!reponse.ok) throw new Error(data.erreur || "Erreur inconnue");
  return data;
}

function vider(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function equipeDe(etat, camp) {
  return camp === "humain" ? etat.joueur_humain.equipe : etat.joueur_ia.equipe;
}

function trouverCombattant(etat, id) {
  return (
    etat.joueur_humain.equipe.find((c) => c.id === id) ||
    etat.joueur_ia.equipe.find((c) => c.id === id)
  );
}

function roleDe(etat, camp) {
  return etat.j1 === camp ? "J1" : "J2";
}

/** Conditions verifiables avant la resolution. Victoire / Defaite / Surpuissance dependent
 *  de l'issue de la bataille : elles ne sont jamais affichees comme validees. */
function conditionEstValidee(pouvoir, role, pvSoi, pvAdv, prochaineUtilisation) {
  if (!pouvoir) return false;
  switch (pouvoir.condition) {
    case "courage":
      return role === "J1";
    case "riposte":
      return role === "J2";
    case "vengeance":
      return pvAdv > pvSoi;
    case "domination":
      return pvAdv < pvSoi;
    case "premiere_fois":
      return prochaineUtilisation === 1;
    case "seconde_fois":
      return prochaineUtilisation === 2;
    default:
      return false;
  }
}

/** Les ronds sous la carte materialisent les 2 utilisations du Combattant sur la partie
 *  (equivalent de la carte inclinee du jeu physique). */
function rondsUtilisation(data) {
  const total = data.utilisations_max || 2;
  let html = "";
  for (let i = 0; i < total; i += 1) {
    html += `<span class="rond-utilisation ${i < data.utilisations ? "consomme" : ""}"></span>`;
  }
  return html;
}

function creerCarteCombattant(data, options = {}) {
  const {
    selectionnable = false, selectionnee = false, indisponible = false,
    engage = false, revele = false, conditionValidee = false, onClick = null,
  } = options;

  const carte = document.createElement("div");
  carte.className = "carte-combattant";
  if (selectionnable) carte.classList.add("selectionnable");
  if (selectionnee) carte.classList.add("selectionnee");
  if (indisponible) carte.classList.add("indisponible");
  if (engage) carte.classList.add("engage");
  if (revele) carte.classList.add("revele");
  if (conditionValidee) carte.classList.add("condition-validee");

  const titre = document.createElement("h4");
  titre.textContent = data.nom;
  carte.appendChild(titre);

  const stats = document.createElement("div");
  stats.className = "stats-combattant";
  stats.innerHTML =
    `<span>Puissance <b>${data.puissance}</b></span><span>Degats <b>${data.degats}</b></span>`;
  carte.appendChild(stats);

  if (data.pouvoir) {
    const pouvoir = document.createElement("p");
    pouvoir.className = "pouvoir-combattant";
    pouvoir.textContent = data.pouvoir.description;
    carte.appendChild(pouvoir);
  }

  if (data.utilisations !== undefined) {
    const ronds = document.createElement("div");
    ronds.className = "ronds-utilisation";
    ronds.innerHTML = rondsUtilisation(data);
    ronds.title = `${data.utilisations} / ${data.utilisations_max || 2} utilisations`;
    carte.appendChild(ronds);
  }

  if (revele) {
    const badge = document.createElement("span");
    badge.className = "badge-revele";
    badge.textContent = "Revele";
    carte.appendChild(badge);
  }

  if (onClick) carte.addEventListener("click", onClick);
  return carte;
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
      creerCarteCombattant(c, {
        selectionnable: true,
        selectionnee: equipeSelectionnee.has(c.id),
        onClick: () => toggleSelection(c.id),
      })
    );
  });
  document.getElementById("compteur-selection").textContent =
    `${equipeSelectionnee.size} / 4 selectionnes`;
  document.getElementById("btn-lancer-partie").disabled = equipeSelectionnee.size !== 4;
}

function toggleSelection(id) {
  if (equipeSelectionnee.has(id)) equipeSelectionnee.delete(id);
  else if (equipeSelectionnee.size < 4) equipeSelectionnee.add(id);
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

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "bataille_resolue") {
    renderFin(etat);
    return;
  }
  if (etat.phase !== "choix_duo") duoSelectionne = [];
  if (etat.phase !== "ciblage") ciblagesEnCours = {};
  renderTableauBord(etat);
  renderCarteBataille(etat);
  renderEquipes(etat);
  renderCentre(etat);
}

function pvRonds(pv, max) {
  const surplus = Math.max(0, pv - max);
  const pleins = Math.max(0, Math.min(pv, max));
  let html = "";
  for (let i = 0; i < max; i += 1) {
    html += `<span class="pv-rond ${i < pleins ? "plein" : ""}"></span>`;
  }
  for (let i = 0; i < surplus; i += 1) html += `<span class="pv-rond surplus"></span>`;
  return html;
}

function renderTableauBord(etat) {
  const max = etat.pv_depart;
  document.getElementById("pv-humain-texte").textContent = `${etat.joueur_humain.pv} PV`;
  document.getElementById("pv-ia-texte").textContent = `${etat.joueur_ia.pv} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(etat.joueur_humain.pv, max);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(etat.joueur_ia.pv, max);
  document.getElementById("tour-texte").textContent =
    `Bataille ${Math.min(etat.tour, etat.tours_max)} / ${etat.tours_max}`;
  document.getElementById("role-texte").textContent =
    etat.j1 === "humain" ? "Tu resous tes Pouvoirs en premier (J1)" : "L'IA resout ses Pouvoirs en premier (J1)";
}

function renderCarteBataille(etat) {
  const bloc = document.getElementById("carte-bataille");
  const carte = etat.carte_bataille;
  bloc.innerHTML =
    `<span class="carte-bataille-libelle">Carte bataille de ce tour</span>` +
    `<span class="carte-bataille-nom">${carte.nom}</span>` +
    `<span class="carte-bataille-desc">${carte.description}</span>` +
    `<span class="carte-bataille-note">Effet applique par le vainqueur de la bataille</span>`;
}

function renderEquipes(etat) {
  const choixOuvert = etat.phase === "choix_duo" && etat.duo_humain === null;
  const engagesHumain = etat.duo_humain || [];
  const engagesIa = etat.duo_ia || [];
  const reveles = etat.duo_ia_revele || [];

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const selectionnable = choixOuvert && peutEtreClique(etat, c);
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable,
        selectionnee: duoSelectionne.includes(c.id),
        indisponible: choixOuvert && !selectionnable,
        engage: engagesHumain.includes(c.id),
        conditionValidee: conditionEstValidee(
          c.pouvoir, roleDe(etat, "humain"), etat.joueur_humain.pv, etat.joueur_ia.pv,
          c.utilisations + 1
        ),
        onClick: selectionnable ? () => basculerDuo(c.id) : null,
      })
    );
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((c) => {
    grilleIa.appendChild(
      creerCarteCombattant(c, {
        engage: engagesIa.includes(c.id),
        revele: engagesIa.length === 0 && reveles.includes(c.id),
        indisponible: !c.disponible,
        conditionValidee: conditionEstValidee(
          c.pouvoir, roleDe(etat, "ia"), etat.joueur_ia.pv, etat.joueur_humain.pv,
          c.utilisations + 1
        ),
      })
    );
  });
}

/** Un Combattant est cliquable s'il peut completer un duo legal avec la selection en cours.
 *  Les duos legaux sont calcules par le backend : ils excluent ceux qui rendraient une
 *  bataille suivante injouable, faute de 2 Combattants distincts encore disponibles. */
function peutEtreClique(etat, combattant) {
  if (duoSelectionne.includes(combattant.id)) return true;
  if (duoSelectionne.length >= 2 || !combattant.disponible) return false;
  const legaux = etat.duos_legaux || [];
  if (duoSelectionne.length === 0) return legaux.some((duo) => duo.includes(combattant.id));
  return legaux.some((duo) => duo.includes(duoSelectionne[0]) && duo.includes(combattant.id));
}

function basculerDuo(id) {
  const index = duoSelectionne.indexOf(id);
  if (index >= 0) duoSelectionne.splice(index, 1);
  else duoSelectionne.push(id);
  if (duoSelectionne.length === 2) soumettreDuo();
  else render(etatCourant);
}

async function soumettreDuo() {
  const ids = duoSelectionne.slice();
  duoSelectionne = [];
  await appelerApi("/partie/duo", { combattant_ids: ids });
}

async function soumettreCiblages() {
  const ciblages = { ...ciblagesEnCours };
  ciblagesEnCours = {};
  await appelerApi("/partie/ciblage", { ciblages });
}

async function appelerApi(chemin, corps) {
  try {
    const etat = await api(chemin, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    });
    render(etat);
  } catch (erreur) {
    const message = document.getElementById("message-attente");
    message.textContent = erreur.message;
    message.classList.remove("cache");
    message.classList.add("erreur");
  }
}

// ------------------------------------------------------------- zone centrale

function renderCentre(etat) {
  const message = document.getElementById("message-attente");
  const zoneCiblage = document.getElementById("zone-ciblage");
  const zoneResultat = document.getElementById("zone-resultat");
  message.classList.add("cache");
  message.classList.remove("erreur");
  zoneCiblage.classList.add("cache");
  zoneResultat.classList.add("cache");

  renderDuosEnJeu(etat);

  if (etat.phase === "choix_duo") {
    const reveles = (etat.duo_ia_revele || []).map((id) => trouverCombattant(etat, id).nom);
    const restantes = etat.batailles_restantes;
    let texte = duoSelectionne.length === 1
      ? "Choisis le second Combattant de ton duo."
      : "Choisis les 2 Combattants que tu engages dans cette bataille.";
    if (reveles.length) {
      texte += ` L'IA a deja verrouille son duo et revele ${reveles.join(" et ")}.`;
    }
    if (restantes === 1) texte += " Derniere bataille.";
    message.textContent = texte;
    message.classList.remove("cache");
  } else if (etat.phase === "ciblage") {
    renderCiblage(etat);
    zoneCiblage.classList.remove("cache");
  } else if (etat.phase === "bataille_resolue") {
    renderResultat(etat);
    zoneResultat.classList.remove("cache");
  }
}

function renderDuosEnJeu(etat) {
  const conteneur = document.getElementById("duos-en-jeu");
  vider(conteneur);
  const resultat = etat.dernier_resultat;

  [
    { camp: "humain", libelle: "Ton duo", ids: etat.duo_humain },
    { camp: "ia", libelle: "Duo de l'IA", ids: etat.duo_ia },
  ].forEach(({ camp, libelle, ids }) => {
    const panneau = document.createElement("div");
    panneau.className = "panneau-duo";
    const infoCamp = resultat ? resultat.camps[camp] : null;
    if (infoCamp && infoCamp.gagnant) panneau.classList.add("gagnant");

    const entete = document.createElement("div");
    entete.className = "panneau-duo-entete";
    const role = resultat ? infoCamp.role : roleDe(etat, camp);
    entete.innerHTML = `<span class="panneau-duo-titre">${libelle}</span>` +
      `<span class="panneau-duo-role">${role}</span>`;
    panneau.appendChild(entete);

    if (!ids || ids.length === 0) {
      const attente = document.createElement("p");
      attente.className = "panneau-duo-attente";
      attente.textContent = camp === "ia" ? "Duo verrouille, face cachee" : "Duo a choisir";
      panneau.appendChild(attente);
    } else if (infoCamp) {
      infoCamp.combattants.forEach((c) => panneau.appendChild(carteResolution(c, infoCamp)));
      panneau.appendChild(totalCamp(infoCamp));
    } else {
      ids.forEach((id) => {
        const data = trouverCombattant(etat, id);
        const carte = document.createElement("div");
        carte.className = "carte-engagee";
        carte.innerHTML = `<h5>${data.nom}</h5>` +
          `<span class="carte-engagee-stats">Puissance ${data.puissance} / Degats ${data.degats}</span>` +
          `<span class="carte-engagee-utilisation">${
            data.utilisations >= 2 ? "Seconde fois" : "Premiere fois"
          }</span>`;
        panneau.appendChild(carte);
      });
    }
    conteneur.appendChild(panneau);
  });
}

function formaterDetail(detail) {
  return detail
    .map(([label, valeur], i) => {
      const texte = i === 0 ? `${valeur}` : `${valeur >= 0 ? "+" : "-"} ${Math.abs(valeur)}`;
      return `<li>${texte} <span class="detail-label">(${label})</span></li>`;
    })
    .join("");
}

function carteResolution(combattant, infoCamp) {
  const carte = document.createElement("div");
  carte.className = "carte-engagee";
  if (combattant.stoppe) carte.classList.add("stoppee");
  let html = `<h5>${combattant.nom}</h5>` +
    `<span class="carte-engagee-utilisation">${
      combattant.n_utilisation === 1 ? "Premiere fois" : "Seconde fois"
    }</span>` +
    `<div class="bloc-stat"><span class="valeur-grosse">${combattant.puissance}</span>` +
    `<span class="libelle-stat">Puissance</span></div>` +
    `<ul class="detail-liste">${formaterDetail(combattant.detail_puissance)}</ul>`;
  if (combattant.cible_nom) {
    html += `<span class="carte-engagee-cible">Cible : ${combattant.cible_nom}</span>`;
  }
  if (infoCamp.gagnant) {
    html += `<div class="bloc-stat degats"><span class="valeur-grosse petite">${combattant.degats}</span>` +
      `<span class="libelle-stat">Degats</span></div>` +
      `<ul class="detail-liste degats">${formaterDetail(combattant.detail_degats)}</ul>`;
  }
  carte.innerHTML = html;
  return carte;
}

function totalCamp(infoCamp) {
  const bloc = document.createElement("div");
  bloc.className = "total-camp";
  let html = `<span class="total-camp-libelle">Puissance du duo</span>` +
    `<span class="total-camp-valeur">${infoCamp.puissance_totale}</span>`;
  if (infoCamp.gagnant) {
    const detail = infoCamp.detail_degats_camp.length
      ? ` (dont ${infoCamp.detail_degats_camp.map(([l, v]) => `+${v} ${l}`).join(", ")})`
      : "";
    html += `<span class="total-camp-degats">Degats infliges : ${infoCamp.degats_totaux}${detail}</span>`;
  }
  bloc.innerHTML = html;
  return bloc;
}

// ---------------------------------------------------------------- ciblage

function renderCiblage(etat) {
  const zone = document.getElementById("zone-ciblage");
  vider(zone);
  const titre = document.createElement("p");
  titre.className = "zone-ciblage-titre";
  titre.textContent =
    "Les deux duos sont reveles. Designe la cible des Pouvoirs a cible unique :";
  zone.appendChild(titre);

  etat.ciblages_requis.forEach((requis) => {
    const ligne = document.createElement("div");
    ligne.className = "ligne-ciblage";
    const source = document.createElement("div");
    source.className = "ciblage-source";
    source.innerHTML = `<b>${requis.nom}</b><span>${requis.pouvoir}</span>`;
    ligne.appendChild(source);

    const cibles = document.createElement("div");
    cibles.className = "ciblage-cibles";
    requis.cibles.forEach((cible) => {
      const bouton = document.createElement("button");
      bouton.className = "bouton-cible";
      if (ciblagesEnCours[requis.combattant_id] === cible.id) {
        bouton.classList.add("choisie");
      }
      bouton.textContent = cible.nom;
      bouton.addEventListener("click", () => {
        ciblagesEnCours[requis.combattant_id] = cible.id;
        if (etat.ciblages_requis.every((r) => ciblagesEnCours[r.combattant_id])) {
          soumettreCiblages();
        } else {
          renderCiblage(etat);
        }
      });
      cibles.appendChild(bouton);
    });
    ligne.appendChild(cibles);
    zone.appendChild(ligne);
  });
}

// --------------------------------------------------------------- resultat

function renderResultat(etat) {
  const resultat = etat.dernier_resultat;
  const journal = document.getElementById("journal-resolution");
  vider(journal);
  resultat.log.forEach((ligne) => {
    const p = document.createElement("p");
    if (ligne.includes("remporte la bataille")) p.className = "gain";
    else if (ligne.startsWith(resultat.carte_bataille.nom)) p.className = "carte";
    p.textContent = ligne;
    journal.appendChild(p);
  });
  const bouton = document.getElementById("btn-bataille-suivante");
  bouton.textContent = etat.terminee ? "Voir le resultat final" : "Bataille suivante";
  bouton.onclick = etat.terminee ? () => renderFin(etat) : batailleSuivante;
}

async function batailleSuivante() {
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
