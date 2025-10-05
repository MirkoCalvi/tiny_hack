using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;
using UnityEngine;

/// <summary>
/// Listens to a WebSocket feed of detection messages and keeps a prefab instance in sync for each unique identifier.
/// All Unity calls run on the main thread while network and JSON work stay on the background client.
/// </summary>

public interface ITrackedObjectSource
{
    int GetTrackedObjects(List<WebSocketObjectSpawner.TrackedObjectInfo> buffer);
    bool TryGetTrackedObject(string key, out WebSocketObjectSpawner.TrackedObjectInfo info);
}

public class WebSocketObjectSpawner : MonoBehaviour, ITrackedObjectSource
{
    [Serializable]
    public class LabelPrefab
    {
        /// <summary>
        /// Text label expected from the detector payload.
        /// </summary>
        public string label;
        /// <summary>
        /// Prefab to spawn when the label is received.
        /// </summary>
        public GameObject prefab;
    }

    [Serializable]
    private class DetectionMessage
    {
        /// <summary>
        /// Should be "detection" or "od"; empty values are treated as valid.
        /// </summary>
        public string type;
        public string device;
        public string label;
        public float x;
        public float y;
        public float z;
        public double timestamp;
    }

    [Serializable]
    private class EnvelopeMessage
    {
        public string source;
        public DetectionMessage payload;
        public DetectionMessage detection;
    }

    public string websocketUri = "ws://127.0.0.1:8765";
    public GameObject defaultPrefab;
    public List<LabelPrefab> labelPrefabs = new();
    [SerializeField] bool enableDebugLogging;

    const int MaxMessagesPerFrame = 32;
    readonly ConcurrentQueue<string> pendingRawMessages = new();
    readonly ConcurrentQueue<string> pendingDebugLogs = new();
    readonly ConcurrentQueue<Exception> pendingExceptions = new();
    readonly Dictionary<string, SpawnEntry> activeEntries = new();
    readonly List<string> cleanupKeys = new();
    readonly List<string> trackedKeys = new();

    [SerializeField, Min(0f)] float positionSmoothTime = 0.15f;

    ClientWebSocket socket;
    CancellationTokenSource cancellation;

    /// <summary>
    /// Tracks runtime state for a spawned prefab keyed by the detection identifier.
    /// </summary>
    class SpawnEntry
    {
        public string Label;
        public string Device;
        public string Key;
        public GameObject Instance;
        public Vector3 Target;
        public Vector3 Velocity;
    }

    void Awake()
    {
        Application.runInBackground = true;
    }

    void OnEnable()
    {
        cancellation = new CancellationTokenSource();
        _ = ReceiveLoop(cancellation.Token);
    }

    void OnDisable()
    {
        cancellation?.Cancel();
        cancellation = null;
    }

    /// <summary>
    /// Background task that handles socket connect/read and queues raw JSON for the main thread.
    /// </summary>
    async Task ReceiveLoop(CancellationToken token)
    {
        using var ws = new ClientWebSocket();
        socket = ws;
        try
        {
            await ws.ConnectAsync(new Uri(websocketUri), token).ConfigureAwait(false);
            EnqueueDebug($"Connected to {websocketUri}");
            var buffer = new byte[4096];
            while (!token.IsCancellationRequested && ws.State == WebSocketState.Open)
            {
                var builder = new StringBuilder();
                WebSocketReceiveResult result;
                do
                {
                    result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), token).ConfigureAwait(false);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, token).ConfigureAwait(false);
                        EnqueueDebug("Server requested close.");
                        return;
                    }
                    builder.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                }
                while (!result.EndOfMessage);
                var message = builder.ToString();
                if (string.IsNullOrWhiteSpace(message))
                {
                    continue;
                }
                pendingRawMessages.Enqueue(message);
                if (System.Threading.Volatile.Read(ref enableDebugLogging))
                {
                    pendingDebugLogs.Enqueue($"Queued payload: {TruncateForLog(message, 200)}");
                }
            }
        }
        catch (OperationCanceledException)
        {
            EnqueueDebug("Receive loop cancelled.");
        }
        catch (Exception ex)
        {
            pendingExceptions.Enqueue(ex);
        }
        finally
        {
            socket = null;
        }
    }

    /// <summary>
    /// Processes queued payloads, applies movement smoothing, and drives prefab lifecycles.
    /// </summary>
    void Update()
    {
        FlushExceptions();
        FlushDebugLogs();

        var processed = 0;
        while (processed < MaxMessagesPerFrame && pendingRawMessages.TryDequeue(out var raw))
        {
            processed++;
            if (!TryGetDetection(raw, out var detection))
            {
                if (enableDebugLogging)
                {
                    Debug.LogWarning($"[WebSocketObjectSpawner] Ignored payload without detection data: {TruncateForLog(raw, 200)}");
                }
                continue;
            }
            if (!IsSupportedDetectionType(detection.type))
            {
                if (enableDebugLogging)
                {
                    Debug.Log($"[WebSocketObjectSpawner] Ignored unsupported message type '{detection.type}' with label '{detection.label}'.");
                }
                continue;
            }
            var key = BuildKey(detection);
            var targetPosition = new Vector3(detection.x, detection.y, detection.z);
            var entry = GetOrCreateEntry(key, detection.label, detection.device, targetPosition);
            entry.Target = targetPosition;
            EnsureInstance(entry, targetPosition);
            if (enableDebugLogging)
            {
                Debug.Log($"[WebSocketObjectSpawner] Updated {entry.Key} => {targetPosition}");
            }
        }

        InterpolateMovement();
    }

    public GameObject GetPrefabForLabel(string label)
    {
        if (!string.IsNullOrEmpty(label))
        {
            foreach (var entry in labelPrefabs)
            {
                if (entry != null && entry.label == label && entry.prefab != null)
                {
                    return entry.prefab;
                }
            }
        }

        return defaultPrefab;
    }

    GameObject ResolvePrefab(string label)
    {
        var prefab = GetPrefabForLabel(label);
        if (prefab != null)
        {
            LogDebug($"Using prefab '{prefab.name}' for label '{label}'.");
            return prefab;
        }
        LogDebug($"Default prefab missing. Creating primitive cube for label '{label}'.");
        return GameObject.CreatePrimitive(PrimitiveType.Cube);
    }

    SpawnEntry GetOrCreateEntry(string key, string label, string device, Vector3 targetPosition)
    {
        if (string.IsNullOrEmpty(key))
        {
            key = GenerateUniqueKey(label ?? "object");
        }

        if (activeEntries.TryGetValue(key, out var existing))
        {
            return existing;
        }

        var prefab = ResolvePrefab(label);
        var instance = Instantiate(prefab);
        instance.name = key;
        instance.transform.position = targetPosition;

        var entry = new SpawnEntry
        {
            Label = label ?? string.Empty,
            Device = device ?? string.Empty,
            Key = key,
            Instance = instance,
            Target = targetPosition,
            Velocity = Vector3.zero
        };

        activeEntries[key] = entry;
        if (!trackedKeys.Contains(key))
        {
            trackedKeys.Add(key);
        }
        LogDebug($"Spawned new instance for {key}.");
        return entry;
    }

    void EnsureInstance(SpawnEntry entry, Vector3 targetPosition)
    {
        if (entry.Instance != null)
        {
            return;
        }

        var prefab = ResolvePrefab(entry.Label);
        entry.Instance = Instantiate(prefab);
        entry.Instance.name = entry.Key;
        entry.Instance.transform.position = targetPosition;
        entry.Velocity = Vector3.zero;
        LogDebug($"Recreated instance for {entry.Key}.");
    }

    string GenerateUniqueKey(string baseKey)
    {
        var key = string.IsNullOrEmpty(baseKey) ? "object" : baseKey;
        if (!activeEntries.ContainsKey(key) && !trackedKeys.Contains(key))
        {
            return key;
        }

        var index = 1;
        string candidate;
        do
        {
            candidate = string.Concat(key, "#", index);
            index++;
        }
        while (activeEntries.ContainsKey(candidate) || trackedKeys.Contains(candidate));

        return candidate;
    }

    void FlushExceptions()
    {
        while (pendingExceptions.TryDequeue(out var ex))
        {
            Debug.LogError($"[WebSocketObjectSpawner] {ex}");
        }
    }

    void FlushDebugLogs()
    {
        if (!enableDebugLogging)
        {
            while (pendingDebugLogs.TryDequeue(out _))
            {
            }
            return;
        }
        while (pendingDebugLogs.TryDequeue(out var message))
        {
            Debug.Log($"[WebSocketObjectSpawner] {message}");
        }
    }

    void LogDebug(string message)
    {
        if (!enableDebugLogging)
        {
            return;
        }
        Debug.Log($"[WebSocketObjectSpawner] {message}");
    }

    void EnqueueDebug(string message)
    {
        if (System.Threading.Volatile.Read(ref enableDebugLogging))
        {
            pendingDebugLogs.Enqueue(message);
        }
    }

    static string TruncateForLog(string value, int maxLength)
    {
        if (string.IsNullOrEmpty(value) || value.Length <= maxLength)
        {
            return value;
        }
        return value.Substring(0, maxLength) + "...";
    }

    static bool TryGetDetection(string raw, out DetectionMessage detection)
    {
        detection = null;
        if (string.IsNullOrEmpty(raw))
        {
            return false;
        }
        try
        {
            detection = JsonUtility.FromJson<DetectionMessage>(raw);
        }
        catch
        {
            detection = null;
        }
        if (IsValidDetection(detection))
        {
            return true;
        }
        try
        {
            var envelope = JsonUtility.FromJson<EnvelopeMessage>(raw);
            detection = envelope?.payload ?? envelope?.detection;
        }
        catch
        {
            detection = null;
        }
        return IsValidDetection(detection);
    }

    static bool IsValidDetection(DetectionMessage detection)
    {
        return detection != null && !string.IsNullOrEmpty(detection.label);
    }

    static bool IsSupportedDetectionType(string type)
    {
        if (string.IsNullOrEmpty(type))
        {
            return true;
        }

        switch (type)
        {
            case "detection":
            case "od":
                return true;
            default:
                return false;
        }
    }

    /// <summary>
    /// Lightweight snapshot of a spawned prefab used by other systems to query state.
    /// </summary>
    public readonly struct TrackedObjectInfo
    {
        public TrackedObjectInfo(string key, GameObject instance, Vector3 position, Vector3 targetPosition)
        {
            Key = key;
            Instance = instance;
            Position = position;
            TargetPosition = targetPosition;
        }

        public string Key { get; }
        public GameObject Instance { get; }
        public Vector3 Position { get; }
        public Vector3 TargetPosition { get; }
    }

    /// <summary>
    /// Copies the current tracked entries into <paramref name="buffer"/> and returns the number copied.
    /// </summary>
    public int GetTrackedObjects(List<TrackedObjectInfo> buffer)
    {
        if (buffer == null)
        {
            throw new ArgumentNullException(nameof(buffer));
        }

        buffer.Clear();
        foreach (var key in trackedKeys)
        {
            if (!activeEntries.TryGetValue(key, out var entry))
            {
                continue;
            }

            var instance = entry.Instance;
            var currentPosition = instance != null ? instance.transform.position : entry.Target;
            buffer.Add(new TrackedObjectInfo(entry.Key, instance, currentPosition, entry.Target));
        }
        return buffer.Count;
    }

    /// <summary>
    /// Attempts to find a tracked entry by key, device::label, prefab name, or raw label.
    /// </summary>
    public bool TryGetTrackedObject(string key, out TrackedObjectInfo info)
    {
        info = default;
        if (string.IsNullOrWhiteSpace(key))
        {
            return false;
        }

        var trimmed = key.Trim();

        if (activeEntries.TryGetValue(trimmed, out var direct))
        {
            var instance = direct.Instance;
            var currentPosition = instance != null ? instance.transform.position : direct.Target;
            info = new TrackedObjectInfo(direct.Key, instance, currentPosition, direct.Target);
            return true;
        }

        foreach (var entry in activeEntries.Values)
        {
            if (MatchesEntryIdentifier(entry, trimmed))
            {
                var instance = entry.Instance;
                var currentPosition = instance != null ? instance.transform.position : entry.Target;
                info = new TrackedObjectInfo(entry.Key, instance, currentPosition, entry.Target);
                return true;
            }
        }

        return false;
    }

    bool MatchesEntryIdentifier(SpawnEntry entry, string identifier)
    {
        if (entry == null)
        {
            return false;
        }

        if (!string.IsNullOrEmpty(entry.Key) && string.Equals(entry.Key, identifier, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        if (entry.Instance != null && string.Equals(entry.Instance.name, identifier, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        if (!string.IsNullOrEmpty(entry.Device))
        {
            var deviceKey = string.Concat(entry.Device, "::", entry.Label ?? string.Empty);
            if (string.Equals(deviceKey, identifier, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        if (!string.IsNullOrEmpty(entry.Label) && string.Equals(entry.Label, identifier, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return false;
    }

    string BuildKey(DetectionMessage detection)
    {
        var label = detection.label ?? string.Empty;
        if (!string.IsNullOrEmpty(detection.device))
        {
            return string.Concat(detection.device, "::", label);
        }
        return label;
    }

    void InterpolateMovement()
    {
        if (activeEntries.Count == 0)
        {
            return;
        }

        var instantMove = positionSmoothTime <= 0f;
        cleanupKeys.Clear();

        foreach (var entry in activeEntries.Values)
        {
            var instance = entry.Instance;
            if (instance == null)
            {
                cleanupKeys.Add(entry.Key);
                continue;
            }

            var target = entry.Target;
            var current = instance.transform.position;

            if (instantMove)
            {
                instance.transform.position = target;
                entry.Velocity = Vector3.zero;
                continue;
            }

            var velocity = entry.Velocity;
            var newPosition = Vector3.SmoothDamp(current, target, ref velocity, positionSmoothTime, Mathf.Infinity, Time.deltaTime);
            instance.transform.position = newPosition;
            entry.Velocity = velocity;
        }

        if (cleanupKeys.Count > 0)
        {
            foreach (var key in cleanupKeys)
            {
                if (!activeEntries.TryGetValue(key, out var entry))
                {
                    continue;
                }

                activeEntries.Remove(key);
                trackedKeys.Remove(key);
            }
            cleanupKeys.Clear();
        }
    }
}
