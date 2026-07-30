// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;
let glypheSelectionneId = null;
let combattantSelectionneId = null;

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

function rondsEnergie(energie) {
  return Array.from({ length: energie }, () => `<span class="rond-energie"></span>`).join("");
}

function seuilEnergieInfo(energieMin) {
  if (energieMin > 0) {
    return { html: rondsEnergie(energieMin), titre: `Energie ${energieMin} ou plus` };
  }
  return { html: `<span class="rond-energie rond-energie-vide"></span>`, titre: "Toujours actif" };
}

function creerCarteGlyphe(glyphe, onClick, { selectionnee = false } = {}) {
  const carte = document.createElement("div");
  carte.className = "carte-glyphe";
  if (selectionnee) carte.classList.add("selectionnee");
  carte.innerHTML = `<div class="glyphe-puissance">${glyphe.puissance}</div><div class="glyphe-energie">${rondsEnergie(glyphe.energie)}</div>`;
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
  // Si les selections en cours ne correspondent plus a l'etat actuel (nouvelle manche,
  // ou plus qu'un seul choix possible), on les reinitialise / auto-selectionne.
  const peutChoisir = peutChoisirMaintenant(etat);
  const main = (peutChoisir && etat.joueur_humain.main_glyphes) || [];
  if (!main.some((g) => g.id === glypheSelectionneId)) {
    glypheSelectionneId = main.length === 1 ? main[0].id : null;
  }
  const dispo = (peutChoisir && etat.joueur_humain.equipe.filter((c) => !c.utilise)) || [];
  if (!dispo.some((c) => c.id === combattantSelectionneId)) {
    combattantSelectionneId = dispo.length === 1 ? dispo[0].id : null;
  }
  renderTableauBord(etat);
  renderGlyphesRestants(etat);
  renderEquipes(etat);
  renderZoneCentrale(etat);
}

function renderTableauBord(etat) {
  const pvH = etat.joueur_humain.pv;
  const pvI = etat.joueur_ia.pv;
  document.getElementById("pv-humain-texte").textContent = `${pvH} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pvI} PV`;
  document.getElementById("pv-humain-barre").style.width = `${Math.max(0, (pvH / 10) * 100)}%`;
  document.getElementById("pv-ia-barre").style.width = `${Math.max(0, (pvI / 10) * 100)}%`;
  document.getElementById("duel-numero-texte").textContent = `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function renderGlyphesRestants(etat) {
  const conteneur = document.getElementById("glyphes-restants-liste");
  vider(conteneur);
  (etat.glyphes_restants || []).forEach((g) => {
    const el = document.createElement("div");
    el.className = "mini-glyphe";
    if (g.restants === 0) el.classList.add("epuise");
    el.innerHTML = `<span class="mini-glyphe-puissance">${g.puissance}</span><span class="mini-glyphe-energie">${rondsEnergie(g.energie)}</span><span class="mini-glyphe-compte">${g.restants}/${g.total}</span>`;
    conteneur.appendChild(el);
  });
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
        selectionnee: c.id === combattantSelectionneId,
        active,
        conditionValidee: conditionEstValidee(c.pouvoir, roleHumain, etat.joueur_humain.pv, etat.joueur_ia.pv),
        onClick:
          peutChoisir && !c.utilise
            ? () => armerCombattant(c.id)
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

function armerCombattant(id) {
  combattantSelectionneId = id;
  if (glypheSelectionneId !== null) {
    soumettreChoix();
  } else {
    renderEquipes(etatCourant);
    renderZoneCentrale(etatCourant);
  }
}

function armerGlyphe(id) {
  glypheSelectionneId = id;
  if (combattantSelectionneId !== null) {
    soumettreChoix();
  } else {
    renderEquipes(etatCourant);
    renderZoneCentrale(etatCourant);
  }
}

async function soumettreChoix() {
  const combattantId = combattantSelectionneId;
  const glypheId = glypheSelectionneId;
  combattantSelectionneId = null;
  glypheSelectionneId = null;
  const etat = await api("/partie/combattant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ combattant_id: combattantId, glyphe_id: glypheId }),
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
      contenu += `<div class="glyphe-joue"><span class="glyphe-joue-puissance">${infoCote.puissance_glyphe}</span><span class="glyphe-joue-energie">${rondsEnergie(infoCote.energie)}</span></div>`;
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
      contenu += `<div class="glyphe-joue">Puissance ${data.puissance} / Degats ${data.degats}</div>`;
    }
    carte.innerHTML = contenu;
    conteneurDuel.appendChild(carte);
  });

  const libelleGlyphes = document.getElementById("libelle-glyphes");
  const mainGlyphes = document.getElementById("main-glyphes");

  if (etat.phase === "choix_combattant") {
    zoneGlyphes.classList.remove("cache");
    vider(mainGlyphes);

    if (humainId === null) {
      const main = etat.joueur_humain.main_glyphes || [];
      messageAttente.textContent =
        main.length > 1
          ? "Choisis ton Combattant et le Glyphe a lui associer, dans l'ordre de ton choix."
          : "Choisis ton Combattant : ton unique Glyphe en main lui sera associe.";
      libelleGlyphes.textContent = "Ta main de Glyphes pour cette manche :";
      mainGlyphes.classList.remove("inactif");
      main.forEach((g) => {
        mainGlyphes.appendChild(
          creerCarteGlyphe(g, () => armerGlyphe(g.id), { selectionnee: g.id === glypheSelectionneId })
        );
      });
    } else {
      messageAttente.textContent = "En attente du choix de l'IA...";
      libelleGlyphes.textContent = "Glyphe restant en main pour la prochaine manche :";
      mainGlyphes.classList.add("inactif");
      (etat.joueur_humain.main_glyphes || []).forEach((g) => {
        mainGlyphes.appendChild(creerCarteGlyphe(g, null));
      });
    }
    messageAttente.classList.remove("cache");
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
