. as $journal |
(.initial_state | fromjson) as $initial |
(.final_state | fromjson) as $final |
{
  commands: (.commands | length),
  automatic_commands: ([.commands[] | select(.command == "battle.auto_turn")] | length),
  initial_turn: $initial.turn,
  final: ($final | {turn, status, gold, crystals, hero, campaign}),
  stages: [range(1; 4) as $stage |
    ([$journal.commands[] | select((.before | fromjson | .campaign.stage) == $stage)]) as $rows |
    {
      stage: $stage,
      commands: ($rows | length),
      campaign_rests: ([$rows[] | select(.command == "end_turn")] | length),
      enemy_phases: ([$rows[] | select(.command == "battle.end_turn")] | length),
      purchases: [$rows[] | select(.command == "build" or .command == "recruit" or
                                   .command == "replace_troop" or .command == "infuse") |
        {command, args, gold_spent, crystals_spent}],
      net_rest_gold: ([$rows[] | select(.command == "end_turn") | -.gold_spent] | add),
      net_rest_crystals: ([$rows[] | select(.command == "end_turn") | -.crystals_spent] | add),
      spells: [$rows[] | select(.command == "battle.cast") |
        . as $row | (.before | fromjson) as $before | (.after | fromjson) as $after |
        {spell: .args[0], caster: (.kwargs.caster_id // 0),
         mana_spent: ($before.battle.mana - $after.battle.mana),
         healed_hp: (if .args[0] == "heal" then
           ([$after.battle.units[] | select(.id == $row.args[1]) | .hp][0] -
            [$before.battle.units[] | select(.id == $row.args[1]) | .hp][0]) else 0 end)}]
    }],
  battles: [.commands | to_entries[] | select(.value.command == "resolve_battle") |
    (.key + 1) as $command | (.value.before | fromjson) |
    {command: $command, stage: .campaign.stage, turn, kind: .battle_kind,
     province: .battle_province, rounds: .battle.round, outcome: .battle.outcome,
     mana: .battle.mana,
     fallen: [.battle.units[] | select(.team == "player" and .id != 0 and .hp == 0) | {id, kind}]}],
  observations: .observations,
  scope: "Agent-directed continuation from the retained historical turn-6 autoplay opening. Stage command counts attribute each advance to its departure stage. No human, alternate-route, recovery, balance or release-readiness claim."
}
