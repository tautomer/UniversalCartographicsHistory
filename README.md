# Elite: Dangerous Universal Cartographics History

As an explorer, I often find it's sad that we can't have a list of all the
star systems and the bodies we discovered or mapped before. I have been
thinking of writing a script like this for quite a long time. Unfortunately, I
couldn't find a way to know whether the bodies had been discovered before.

[Thanks to user `aggasalk` on reddit for the hint!](https://www.reddit.com/r/EliteDangerous/comments/mq50zf/daily_qa_ask_and_answer_any_questions_you_have/guf3tkt?utm_source=share&utm_medium=web2x&context=3)
I can finally finish this script.

The script should be fully functional, though many things can be improved quite
a lot.

## How it works

Well, basically finding events like `FSDJump`, `Scan`, `SAAScanComplete` in all
the journal files. Currently the path to the log files are assumed to be the
default path, i.e., `C:\Users\username\Saved Games\Frontier Developments\Elite Dangerous`.
An summary called `Universal Cartographics Histroy Scan.txt` will be saved in
the same folder as the script.

## Known issues

There some well-known systems (the ones with a unique name, not something like
`Col balabala`) where the bodies are shown as undiscovered, or say not
discovered by any one.

For example, the first ever system I ever "honked", `Sharur` in the starting
space.

![Sharur](assets/Sharur.jpg)

In the journal, these bodies are shown as

```text
{ "timestamp":"2020-11-25T21:44:23Z", "event":"Scan", "ScanType":"NavBeaconDetail", "BodyName":"Sharur B A Belt Cluster 4", "BodyID":16, "Parents":[ {"Ring":12}, {"Star":2}, {"Null":0} ], "StarSystem":"Sharur", "SystemAddress":1733187048154, "DistanceFromArrivalLS":41381.868618, "WasDiscovered":false, "WasMapped":false }
```

No one discovered these bodies and the stars and belt clusters are not mappable,
which means I can't distinguish whether they are first discovered by you or not.

On the other hand, the planets in these systems are mappable, so for any bodies
with status of `"WasDiscovered":false` and `"WasMapped":true` are completely
ignored.

If you happen to be the one who actually mapped these bodies... I'm sorry.

## TODO List

* Add cli arguments or a config file to control some key parameter.
* A simple GUI probably?
 