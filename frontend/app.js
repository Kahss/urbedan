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

  const stats = document.createElement("div");
  stats.className = "stats-combattant";
  stats.innerHTML = `<span>Puissance <b>${data.puissance}</b></span><span>Degats <b>${data.degats}</b></span>`;
  carte.appendChild(stats);

  const liste = document.createElement("ul");
  liste.className = "liste-pouvoirs";
  data.pouvoirs.forEach((p) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="num">Energie ${p.numero}</span>${p.description}`;
    liste.appendChild(li);
  });
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

function creerCarteGlyphe(glyphe, onClick) {
  const carte = document.createElement("div");
  carte.className = "carte-glyphe";
  const pouvoirActive = glyphe.energie > 0 ? `Active Energie ${glyphe.energie}` : "Aucun Pouvoir";
  carte.innerHTML = `<div class="notation">${glyphe.notation}</div><div class="label">Puissance ${glyphe.puissance}</div><div class="label">${pouvoirActive}</div>`;
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
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderEquipes(etat);
  renderZoneCentrale(etat);
}

function renderTableauBord(etat) {
  const pvH = etat.joueur_humain.pv;
  const pvI = etat.joueur_ia.pv;
  document.getElementById("pv-humain-texte").textContent = `${pvH} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pvI} PV`;
  document.getElementById("pv-humain-barre").style.width = `${Math.max(0, (pvH / 12) * 100)}%`;
  document.getElementById("pv-ia-barre").style.width = `${Math.max(0, (pvI / 12) * 100)}%`;
  document.getElementById("duel-numero-texte").textContent = `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function renderEquipes(etat) {
  const humainSlot = humanRole(etat);
  const humainChoisiId = etat["combattant_" + humainSlot];
  const peutChoisir = etat.phase === "choix_combattant" && humainChoisiId === null;

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable: peutChoisir && !c.utilise,
        active,
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
    grilleIa.appendChild(creerCarteCombattant(c, { active }));
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

function renderZoneCentrale(etat) {
  const zoneGlyphes = document.getElementById("zone-glyphes");
  const zoneResultat = document.getElementById("zone-resultat");
  const messageAttente = document.getElementById("message-attente");
  const conteneurDuel = document.getElementById("combattants-en-duel");

  zoneGlyphes.classList.add("cache");
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
      contenu += `<div class="glyphe-joue">Glyphe ${infoCote.glyphe}</div>`;
      const pouvoirActif = infoCote.energie > 0 ? data.pouvoirs.find((p) => p.numero === infoCote.energie) : null;
      contenu += `<div class="pouvoir-actif">${
        pouvoirActif
          ? `Pouvoir selectionne : ${pouvoirActif.description}`
          : "Aucun Pouvoir selectionne (Energie 0)"
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
      contenu += `<div class="glyphe-joue">Puissance ${data.puissance} / Degats ${data.degats}</div>`;
    }
    carte.innerHTML = contenu;
    conteneurDuel.appendChild(carte);
  });

  const libelleGlyphes = document.getElementById("libelle-glyphes");
  const mainGlyphes = document.getElementById("main-glyphes");

  if (etat.phase === "choix_combattant") {
    if (humainId === null) {
      messageAttente.textContent = "Choisis ton Combattant dans ton equipe ci-contre.";
    } else {
      messageAttente.textContent = "En attente du choix de l'IA...";
    }
    messageAttente.classList.remove("cache");

    // Le Glyphe pioche pour ce duel est deja connu : il sera joue automatiquement
    // sur le Combattant choisi, une fois les deux Combattants selectionnes.
    zoneGlyphes.classList.remove("cache");
    libelleGlyphes.textContent = "Ton Glyphe pioche pour ce duel (joue automatiquement une fois ton Combattant choisi) :";
    mainGlyphes.classList.add("inactif");
    vider(mainGlyphes);
    if (etat.joueur_humain.glyphe_courant) {
      mainGlyphes.appendChild(creerCarteGlyphe(etat.joueur_humain.glyphe_courant, null));
    }
  } else if (etat.phase === "duel_resolu") {
    zoneResultat.classList.remove("cache");
    const journal = document.getElementById("journal-resolution");
    vider(journal);
    resultat.log.forEach((ligne) => {
      const p = document.createElement("p");
      if (ligne.startsWith("--") || ligne.startsWith("Puissance totale")) p.className = "titre-etape";
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
