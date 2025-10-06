using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Handles the first level demo logic: watches a tracked "smartphone" object, fires audio cues and logging
/// when it reaches start, finish, and obstacle zones, and supports manual testing with scene objects.
/// </summary>
[DisallowMultipleComponent]
public class Level1Manager : MonoBehaviour
{
    [Header("Tracking")]
    [SerializeField] WebSocketObjectSpawner spawner;
    [SerializeField] string smartphoneIdentifier = "smartphone";
    [SerializeField, Min(0f)] float triggerRadius = 0.15f;
    [SerializeField] bool enableDebugLogging;

    [Header("Anchors")]
    [SerializeField] Transform startPoint;
    [SerializeField] Transform finishPoint;
    [SerializeField] Transform obstaclePoint;

    [Header("Colliders (optional)")]
    [SerializeField] Collider startCollider;
    [SerializeField] Collider finishCollider;
    [SerializeField] Collider obstacleCollider;
    [SerializeField] Collider2D startCollider2D;
    [SerializeField] Collider2D finishCollider2D;
    [SerializeField] Collider2D obstacleCollider2D;

    [Header("Audio (optional)")]
    [SerializeField] AudioSource startAudio;
    [SerializeField] AudioSource finishAudio;
    [SerializeField] AudioSource obstacleAudio;

    readonly List<WebSocketObjectSpawner.TrackedObjectInfo> trackedCache = new(8);
    GameObject manualSmartphone;
    bool manualMissingNotified;

    bool startInside;
    bool finishInside;
    bool obstacleInside;

    Vector3 recordedStartPosition;
    Vector3 recordedFinishPosition;

    public Vector3 InitialPosition => recordedStartPosition;
    public Vector3 FinalPosition => recordedFinishPosition;

    void Awake()
    {
        CacheAnchorAudio();
    }

#if UNITY_EDITOR
    void OnValidate()
    {
        if (!Application.isPlaying)
        {
            CacheAnchorAudio();
            manualSmartphone = null;
            manualMissingNotified = false;
        }
    }
#endif

    /// <summary>
    /// Polls tracking data every frame and routes the smartphone through the configured zones.
    /// </summary>
    void Update()
    {
        if (!TryGetSmartphone(out var info))
        {
            return;
        }

        var position = GetCurrentPosition(info);
        var threshold = triggerRadius;

        UpdateZone(ref startInside,
            IsHit(position, startPoint, startCollider, startCollider2D, threshold),
            position,
            startAudio,
            "Start");

        UpdateZone(ref finishInside,
            IsHit(position, finishPoint, finishCollider, finishCollider2D, threshold),
            position,
            finishAudio,
            "Finish");

        UpdateZone(ref obstacleInside,
            IsHit(position, obstaclePoint, obstacleCollider, obstacleCollider2D, threshold),
            position,
            obstacleAudio,
            "Obstacle");
    }

    /// <summary>
    /// Clears per-zone state so the level can be replayed without reloading the scene.
    /// </summary>
    public void ResetProgress()
    {
        startInside = false;
        finishInside = false;
        obstacleInside = false;
        recordedStartPosition = Vector3.zero;
        recordedFinishPosition = Vector3.zero;
        if (enableDebugLogging)
        {
            Debug.Log("[Level1Manager] Progress reset");
        }
    }

    /// <summary>
    /// Resolves the smartphone position from the WebSocket spawner or a manual scene object.
    /// </summary>
    bool TryGetSmartphone(out WebSocketObjectSpawner.TrackedObjectInfo info)
    {
        info = default;
        var source = ResolveSource();

        if (source != null && !string.IsNullOrWhiteSpace(smartphoneIdentifier))
        {
            var trimmed = smartphoneIdentifier.Trim();
            if (source.TryGetTrackedObject(trimmed, out info))
            {
                if (enableDebugLogging)
                {
                    Debug.Log($"[Level1Manager] Tracking smartphone by id '{trimmed}' at {info.Position}");
                }
                return true;
            }
        }

        if (source != null)
        {
            trackedCache.Clear();
            var count = source.GetTrackedObjects(trackedCache);
            if (count > 0)
            {
                if (string.IsNullOrWhiteSpace(smartphoneIdentifier))
                {
                    info = trackedCache[0];
                    if (enableDebugLogging)
                    {
                        Debug.Log($"[Level1Manager] Using fallback tracked object '{info.Key}' at {info.Position}");
                    }
                    return true;
                }

                var identifier = smartphoneIdentifier.Trim();
                for (var i = 0; i < trackedCache.Count; i++)
                {
                    var candidate = trackedCache[i];
                    if (MatchesIdentifier(candidate.Key, identifier))
                    {
                        info = candidate;
                        if (enableDebugLogging)
                        {
                            Debug.Log($"[Level1Manager] Matched identifier '{identifier}' to '{candidate.Key}' at {info.Position}");
                        }
                        return true;
                    }
                }
            }
        }

        var manualObject = ResolveManualSmartphone();
        if (manualObject != null)
        {
            var position = manualObject.transform.position;
            info = new WebSocketObjectSpawner.TrackedObjectInfo(
                manualObject.name,
                manualObject,
                position,
                position);
            if (enableDebugLogging)
            {
                Debug.Log($"[Level1Manager] Using manual object '{manualObject.name}' at {position}");
            }
            return true;
        }

        if (enableDebugLogging)
        {
            Debug.Log($"[Level1Manager] No tracked object found for identifier '{smartphoneIdentifier}'");
        }
        return false;
    }

    GameObject ResolveManualSmartphone()
    {
        var targetName = string.IsNullOrWhiteSpace(smartphoneIdentifier)
            ? "smartphone"
            : smartphoneIdentifier.Trim();

        if (manualSmartphone != null && manualSmartphone.name.Equals(targetName, System.StringComparison.Ordinal))
        {
            manualMissingNotified = false;
            return manualSmartphone;
        }

        manualSmartphone = GameObject.Find(targetName);
        if (manualSmartphone == null)
        {
            if (enableDebugLogging && !manualMissingNotified)
            {
                Debug.Log($"[Level1Manager] Manual object '{targetName}' not found in scene");
            }
            manualMissingNotified = true;
        }
        else
        {
            manualMissingNotified = false;
        }
        return manualSmartphone;
    }

    ITrackedObjectSource ResolveSource()
    {
        if (spawner != null)
        {
            return spawner;
        }
        return GetComponent<ITrackedObjectSource>();
    }

    void CacheAnchorAudio()
    {
        if (startAudio == null && startPoint != null)
        {
            startAudio = startPoint.GetComponent<AudioSource>();
        }
        if (finishAudio == null && finishPoint != null)
        {
            finishAudio = finishPoint.GetComponent<AudioSource>();
        }
        if (obstacleAudio == null && obstaclePoint != null)
        {
            obstacleAudio = obstaclePoint.GetComponent<AudioSource>();
        }
        if (startCollider == null && startPoint != null)
        {
            startCollider = startPoint.GetComponent<Collider>();
        }
        if (finishCollider == null && finishPoint != null)
        {
            finishCollider = finishPoint.GetComponent<Collider>();
        }
        if (obstacleCollider == null && obstaclePoint != null)
        {
            obstacleCollider = obstaclePoint.GetComponent<Collider>();
        }
        if (startCollider2D == null && startPoint != null)
        {
            startCollider2D = startPoint.GetComponent<Collider2D>();
        }
        if (finishCollider2D == null && finishPoint != null)
        {
            finishCollider2D = finishPoint.GetComponent<Collider2D>();
        }
        if (obstacleCollider2D == null && obstaclePoint != null)
        {
            obstacleCollider2D = obstaclePoint.GetComponent<Collider2D>();
        }
    }

    Vector3 GetCurrentPosition(WebSocketObjectSpawner.TrackedObjectInfo info)
    {
        if (info.Instance != null)
        {
            return info.Instance.transform.position;
        }
        return info.Position;
    }

    /// <summary>
    /// Checks the given position against an optional 3D/2D collider; falls back to a radius test if needed.
    /// </summary>
    bool IsHit(Vector3 position, Transform anchor, Collider volume, Collider2D volume2D, float radius)
    {
        if (volume != null)
        {
            return volume.bounds.Contains(position);
        }

        if (volume2D != null)
        {
            return volume2D.OverlapPoint(position);
        }

        if (anchor == null)
        {
            return false;
        }

        var sqrThreshold = radius > 0f ? radius * radius : 0f;
        return (position - anchor.position).sqrMagnitude <= sqrThreshold;
    }

    void PlayIfAvailable(AudioSource source)
    {
        if (source != null)
        {
            source.Play();
        }
    }

    void UpdateZone(ref bool wasInside, bool isInside, Vector3 position, AudioSource audioSource, string label)
    {
        if (isInside)
        {
            if (!wasInside)
            {
                if (label == "Start")
                {
                    recordedStartPosition = position;
                }
                else if (label == "Finish")
                {
                    recordedFinishPosition = position;
                }

                PlayIfAvailable(audioSource);
                if (enableDebugLogging)
                {
                    Debug.Log($"[Level1Manager] {label} entered at {position}");
                }
            }
            else
            {
                if (label == "Start")
                {
                    recordedStartPosition = position;
                }
                else if (label == "Finish")
                {
                    recordedFinishPosition = position;
                }
                if (enableDebugLogging)
                {
                    Debug.Log($"[Level1Manager] {label} tracking at {position}");
                }
            }
        }
        else if (wasInside && enableDebugLogging)
        {
            Debug.Log($"[Level1Manager] {label} exited");
        }

        wasInside = isInside;
    }

    static bool MatchesIdentifier(string key, string identifier)
    {
        if (string.Equals(key, identifier, System.StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        if (string.IsNullOrEmpty(key))
        {
            return false;
        }

        var separatorIndex = key.LastIndexOf("::", System.StringComparison.Ordinal);
        if (separatorIndex >= 0 && separatorIndex + 2 < key.Length)
        {
            var label = key.Substring(separatorIndex + 2);
            if (string.Equals(label, identifier, System.StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

}
