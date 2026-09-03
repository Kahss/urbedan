// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

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

function creerCarteCombattant(data, { selectionnable = false, selectionnee = false, active = false, conditionValidee = false, onClick = null } = {}) {
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

  const liste = document.createElement("ul");
  liste.className = "liste-pouvoirs";
  if (data.pouvoir) {
    const li = document.createElement("li");
    li.textContent = data.pouvoir.description;
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

function creerCartePuissance(carte) {
  const el = document.createElement("div");
  el.className = "carte-puissance";
  el.innerHTML = `<div class="carte-puissance-nom">${carte.nom}</div><div class="carte-puissance-valeurs"><span class="cp-puissance">+${carte.puissance}</span><span class="cp-malus">${carte.malus} malus</span></div>`;
  return el;
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
    const carte = creerCarteCombattant(
      { ...c, utilise: false },
      {
        selectionnable: true,
        selectionnee: equipeSelectionnee.has(c.id),
        onClick: () => toggleSelection(c.id),
      }
    );
    grille.appendChild(carte);
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

function selectionnerEquipeAleatoire() {
  const idsMelanges = combattantsDisponibles.map((c) => c.id);
  for (let i = idsMelanges.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [idsMelanges[i], idsMelanges[j]] = [idsMelanges[j], idsMelanges[i]];
  }
  equipeSelectionnee.clear();
  idsMelanges.slice(0, 4).forEach((id) => equipeSelectionnee.add(id));
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
  document.getElementById("pv-humain-texte").textContent = `${pvH} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pvI} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(pvH);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(pvI);
  document.getElementById("duel-numero-texte").textContent = `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirMaintenant(etat);
  const roleHumain = humanRole(etat);
  const roleIa = roleHumain === "j1" ? "j2" : "j1";

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable: peutChoisir && !c.utilise,
        active,
        conditionValidee: conditionEstValidee(c.pouvoir, roleHumain, etat.joueur_humain.pv, etat.joueur_ia.pv),
        onClick:
          peutChoisir && !c.utilise
            ? () => choisirCombattant(c.id)
            : null,
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
        conditionValidee: conditionEstValidee(c.pouvoir, roleIa, etat.joueur_ia.pv, etat.joueur_humain.pv),
      })
    );
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

document.getElementById("btn-piocher").addEventListener("click", () => decisionPioche("piocher"));
document.getElementById("btn-arreter").addEventListener("click", () => decisionPioche("arreter"));

function renderZoneCentrale(etat) {
  const zonePioche = document.getElementById("zone-pioche");
  const zoneResultat = document.getElementById("zone-resultat");
  const messageAttente = document.getElementById("message-attente");
  const conteneurDuel = document.getElementById("combattants-en-duel");

  zonePioche.classList.add("cache");
  zoneResultat.classList.add("cache");
  messageAttente.classList.add("cache");
  vider(conteneurDuel);

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
      conteneurDuel.appendChild(placeholder);
      return;
    }
    const data = trouverCombattant(etat, id);
    const carte = document.createElement("div");
    carte.className = "carte-duel";
    let contenu = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;
    if (resultat) {
      const infoCote = resultat.combattant_j1.nom === data.nom ? resultat.combattant_j1 : resultat.combattant_j2;
      const cartesTxt = infoCote.cartes.length
        ? infoCote.cartes.map((c) => `${c.nom} (+${c.puissance}/${c.malus} malus)`).join(", ")
        : "aucune carte piochee";
      contenu += `<div class="cartes-jouees">${cartesTxt}${infoCote.busted ? " — BUST (malus >= 3)" : ""}</div>`;
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
    conteneurDuel.appendChild(carte);
  });

  if (etat.phase === "choix_combattant") {
    messageAttente.textContent =
      humainId === null ? "Choisis ton Combattant pour ce duel." : "En attente du choix de l'IA...";
    messageAttente.classList.remove("cache");
  } else if (etat.phase === "pioche") {
    renderZonePioche(etat, zonePioche, humainSlot, iaSlot);
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

function renderZonePioche(etat, zonePioche, humainSlot, iaSlot) {
  zonePioche.classList.remove("cache");

  const infoHumain = etat.pioche[humainSlot];
  const infoIa = etat.pioche[iaSlot];

  document.getElementById("pioche-tas-restant").textContent = `Cartes restantes dans le tas : ${etat.pioche.cartes_restantes_deck}`;

  const mesCartes = document.getElementById("mes-cartes-piochees");
  vider(mesCartes);
  if (infoHumain.cartes.length === 0) {
    mesCartes.textContent = "Aucune carte piochee pour l'instant.";
  } else {
    infoHumain.cartes.forEach((c) => mesCartes.appendChild(creerCartePuissance(c)));
  }
  document.getElementById("mes-totaux-pioche").textContent =
    `Puissance des cartes : +${infoHumain.puissance_cartes} — Malus total : ${infoHumain.malus_total}` +
    (infoHumain.malus_total >= 3 ? " (BUST, puissance des cartes annulee)" : "");

  document.getElementById("statut-pioche-ia").textContent = `${infoIa.nb_cartes} carte(s) piochee(s)` + (infoIa.arrete ? " — a passe" : " — en train de decider");

  const monTour = etat.pioche.tour === humainSlot;
  const jePeuxAgir = monTour && !infoHumain.arrete;
  document.getElementById("btn-piocher").disabled = !jePeuxAgir || etat.pioche.cartes_restantes_deck === 0;
  document.getElementById("btn-arreter").disabled = !jePeuxAgir;
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
