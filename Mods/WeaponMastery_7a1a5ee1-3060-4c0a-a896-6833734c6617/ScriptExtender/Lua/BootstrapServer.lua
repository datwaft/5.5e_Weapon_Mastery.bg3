local NICK_PASSIVE = "WM55_Known_Nick"
local NICK_READY = "WM55_NICK_READY"
local NICK_USED = "WM55_NICK_USED"
local NICK_OFFHAND_BLOCK = "WM55_NICK_OFFHAND_BLOCK"
local NULL_UUID = "NULL_00000000-0000-0000-0000-000000000000"

local enabled = false
local sequence = 0

local function isNickCharacter(character)
    return character ~= nil
        and character ~= NULL_UUID
        and Osi.HasPassive(character, NICK_PASSIVE) == 1
end

local function snapshot(character)
    local actionPoints = Osi.GetActionResourceValuePersonal(character, "ActionPoint", 0)
    local bonusActionPoints = Osi.GetActionResourceValuePersonal(character, "BonusActionPoint", 0)
    local nickReady = Osi.HasActiveStatus(character, NICK_READY)
    local nickUsed = Osi.HasActiveStatus(character, NICK_USED)
    local offhandBlocked = Osi.HasActiveStatus(character, NICK_OFFHAND_BLOCK)

    return string.format(
        "action=%s bonus=%s ready=%s used=%s blocked=%s",
        tostring(actionPoints),
        tostring(bonusActionPoints),
        tostring(nickReady),
        tostring(nickUsed),
        tostring(offhandBlocked)
    )
end

local function logEvent(eventName, character, storyActionId, details)
    if not enabled or not isNickCharacter(character) then
        return
    end

    sequence = sequence + 1

    Ext.Utils.Print(string.format(
        "[WM55 Nick Debug] #%d event=%s story=%s actor=%s %s %s",
        sequence,
        eventName,
        tostring(storyActionId),
        tostring(character),
        details or "",
        snapshot(character)
    ))
end

Ext.Osiris.RegisterListener("TurnStarted", 1, "after", function (character)
    logEvent("TurnStarted", character, "-", "")
end)

Ext.Osiris.RegisterListener("UsingSpell", 5, "after", function (caster, spell, spellType, spellElement, storyActionId)
    logEvent(
        "UsingSpell",
        caster,
        storyActionId,
        string.format("spell=%s type=%s element=%s", tostring(spell), tostring(spellType), tostring(spellElement))
    )
end)

Ext.Osiris.RegisterListener("UsingSpellOnTarget", 6, "after", function (caster, target, spell, spellType, spellElement, storyActionId)
    logEvent(
        "UsingSpellOnTarget",
        caster,
        storyActionId,
        string.format(
            "target=%s spell=%s type=%s element=%s",
            tostring(target),
            tostring(spell),
            tostring(spellType),
            tostring(spellElement)
        )
    )
end)

Ext.Osiris.RegisterListener("StartAttack", 4, "after", function (defender, attackOwner, attacker, storyActionId)
    logEvent(
        "StartAttack",
        attackOwner,
        storyActionId,
        string.format("defender=%s attacker=%s", tostring(defender), tostring(attacker))
    )
end)

Ext.Osiris.RegisterListener("AttackedBy", 7, "after", function (defender, attackOwner, attacker, damageType, damageAmount, damageCause, storyActionId)
    logEvent(
        "AttackedBy",
        attackOwner,
        storyActionId,
        string.format(
            "defender=%s attacker=%s damageType=%s damage=%s cause=%s",
            tostring(defender),
            tostring(attacker),
            tostring(damageType),
            tostring(damageAmount),
            tostring(damageCause)
        )
    )
end)

Ext.Osiris.RegisterListener("MissedBy", 4, "after", function (defender, attackOwner, attacker, storyActionId)
    logEvent(
        "MissedBy",
        attackOwner,
        storyActionId,
        string.format("defender=%s attacker=%s", tostring(defender), tostring(attacker))
    )
end)

Ext.Osiris.RegisterListener("CastedSpell", 5, "after", function (caster, spell, spellType, spellElement, storyActionId)
    logEvent(
        "CastedSpell",
        caster,
        storyActionId,
        string.format("spell=%s type=%s element=%s", tostring(spell), tostring(spellType), tostring(spellElement))
    )
end)

local function isNickStatus(status)
    return status == NICK_READY
        or status == NICK_USED
        or status == NICK_OFFHAND_BLOCK
end

Ext.Osiris.RegisterListener("StatusApplied", 4, "after", function (object, status, causee, storyActionId)
    if isNickStatus(status) then
        logEvent(
            "StatusApplied",
            object,
            storyActionId,
            string.format("status=%s causee=%s", tostring(status), tostring(causee))
        )
    end
end)

Ext.Osiris.RegisterListener("StatusRemoved", 4, "after", function (object, status, causee, applyStoryActionId)
    if isNickStatus(status) then
        logEvent(
            "StatusRemoved",
            object,
            applyStoryActionId,
            string.format("status=%s causee=%s", tostring(status), tostring(causee))
        )
    end
end)

Ext.RegisterConsoleCommand("wm55_nick_debug", function (_, mode)
    local normalizedMode = string.lower(tostring(mode or ""))

    if normalizedMode == "on" then
        enabled = true
        sequence = 0
        Ext.Utils.Print("[WM55 Nick Debug] enabled; only characters with WM55_Known_Nick will be logged")

        local hostCharacter = Osi.GetHostCharacter()
        logEvent("DebugEnabled", hostCharacter, "-", "")
    elseif normalizedMode == "off" then
        enabled = false
        Ext.Utils.Print("[WM55 Nick Debug] disabled")
    else
        Ext.Utils.Print(string.format(
            "[WM55 Nick Debug] %s; use !wm55_nick_debug on or !wm55_nick_debug off",
            enabled and "enabled" or "disabled"
        ))
    end
end)

Ext.Utils.Print("[WM55 Nick Debug] loaded but disabled; use !wm55_nick_debug on in the server console")
