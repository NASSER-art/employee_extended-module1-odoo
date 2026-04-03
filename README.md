# extension employee moderne-metale (Odoo 16)

## Description

Module d'extension du module Ressources Humaines (hr) pour Odoo 16,
adapté au contexte légal et administratif tunisien.

## Fonctionnalités

### 1. Département et sous-département d'affectation
- Gestion des départements d'affectation indépendants du module hr natif
- Sous-départements liés dynamiquement au département parent
- Vues complètes de configuration (liste, formulaire)

### 2. Niveau d'éducation
- Champs conformes au système éducatif tunisien
- Niveaux : BTP, BTS, CAP, Licence, Master, Ingénieur, Doctorat, Équivalent
- Spécialité, établissement et année d'obtention

### 3. Permis de conduire et alertes
- Suivi complet du permis (numéro, catégorie, dates)
- Statut automatique : Valide / Attention (<30j) / Critique (<15j) / Expiré
- Alerte visuelle dans le formulaire employé
- Badge statut dans le bouton statistique
- Notifications automatiques aux managers RH
- Tâche planifiée quotidienne de vérification
- Menu dédié "Alertes Permis" avec vues liste, kanban, graphique
- Widget systray avec compteur d'alertes

### 4. Informations sociales
- Chef de famille
- Informations conjoint
- CIN : numéro (8 chiffres, unicité vérifiée), pièce jointe
- Numéro CNSS

### 5. Type de contrat (CDI / CDD)

#### CDI (par défaut)
- Période d'essai max 6 mois, renouvelable une seule fois
- Rupture pendant essai sans indemnité
- Validation automatique des contraintes de durée

#### CDD
- Uniquement pour cas exceptionnels (motif obligatoire)
- Pas de période d'essai
- Conversion automatique en CDI si :
  - CDD non conforme (pas de motif)
  - Continuation après fin de contrat sans opposition
- Bouton de conversion manuelle pour les managers

## Sécurité

| Groupe | Lecture | Écriture | Création | Suppression |
|--------|---------|----------|----------|-------------|
| Utilisateur RH | ✅ | ❌ | ❌ | ❌ |
| Manager RH | ✅ | ✅ | ✅ | ✅ |

## Tâches planifiées (Cron)

1. **Vérification permis** : quotidienne, détecte les permis <30 jours
2. **Vérification CDD** : quotidienne, convertit les CDD expirés en CDI
3. **Vérification période d'essai** : quotidienne, marque les essais terminés

## Installation

1. Copier le dossier `employee_extended` dans le répertoire des addons
2. Mettre à jour la liste des modules
3. Installer le module "extension employee moderne-metale"

## Dépendances

- `hr` (Ressources Humaines)
- `hr_contract` (Contrats employés)
- `mail` (Messagerie)
- `web` (Interface Web)

## Compatibilité

- Odoo 16.0 Community et Enterprise