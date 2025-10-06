using System;
using System.Collections.Generic;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

/// <summary>
/// Manages the second-level Rota board: registers pieces, enforces placement/movement turns, checks victory lines,
/// and offers inspector helpers for quickly spawning playable pieces in the scene.
/// </summary>
[DisallowMultipleComponent]
public class Level2Manager : MonoBehaviour
{
    const int BoardSize = 3;

    enum PlayerId
    {
        One,
        Two
    }

    enum GamePhase
    {
        Placement,
        Movement,
        Completed
    }

    [Serializable]
    class PlayerConfig
    {
        public string name = "Player";
        public List<string> pieceIdentifiers = new();
    }

    [Header("Tracking")]
    [SerializeField] WebSocketObjectSpawner spawner;
    [SerializeField] PlayerConfig playerOne = new() { name = "Player One" };
    [SerializeField] PlayerConfig playerTwo = new() { name = "Player Two" };
    [SerializeField] bool enableDebugLogging;

    [Header("Board Mapping")]
    [SerializeField] Vector2 boardOrigin = Vector2.zero;
    [SerializeField] Vector2 cellSize = Vector2.one;
    [SerializeField, Min(0f)] float cellSnapTolerance = 0.15f;

    [Header("Manual Testing")]
    [Tooltip("Use scene objects when WebSocket data is unavailable.")]
    [SerializeField] bool allowManualSceneObjects = true;

    [Header("Debug Spawn Tools")]
    [SerializeField] Vector3 debugSpawnOrigin = new Vector3(-0.5f, 0f, -0.5f);
    [SerializeField] Vector2 debugSpawnSpacing = new Vector2(0.25f, 0.35f);
    [SerializeField] float debugSpawnYOffset;

    readonly Dictionary<string, PieceState> pieces = new();
    readonly Dictionary<Vector2Int, string> occupiedCells = new();
    readonly List<WebSocketObjectSpawner.TrackedObjectInfo> trackedBuffer = new(16);
    readonly Dictionary<string, GameObject> manualLookup = new();

    PlayerId currentPlayer = PlayerId.One;
    GamePhase phase = GamePhase.Placement;
    bool gameFinished;
    PlayerId winner;
    readonly Dictionary<PlayerId, int> remainingPlacements = new();

    public int BoardDimension => BoardSize;
    public Vector2 BoardOrigin => boardOrigin;
    public Vector2 CellDimensions => cellSize;
    public float SnapTolerance => cellSnapTolerance;

    class PieceState
    {
        public PieceState(PlayerId owner, string identifier)
        {
            Owner = owner;
            Identifier = identifier;
        }

        public PlayerId Owner { get; }
        public string Identifier { get; }
        public Vector2Int? BoardPosition { get; set; }
        public Vector3 LastKnownPosition { get; set; }
    }

    static readonly Vector2Int CenterCell = new(1, 1);
    static readonly Vector2Int[][] WinningLines =
    {
        new[] { new Vector2Int(0, 0), new Vector2Int(1, 0), new Vector2Int(2, 0) },
        new[] { new Vector2Int(0, 1), new Vector2Int(1, 1), new Vector2Int(2, 1) },
        new[] { new Vector2Int(0, 2), new Vector2Int(1, 2), new Vector2Int(2, 2) },
        new[] { new Vector2Int(0, 0), new Vector2Int(0, 1), new Vector2Int(0, 2) },
        new[] { new Vector2Int(1, 0), new Vector2Int(1, 1), new Vector2Int(1, 2) },
        new[] { new Vector2Int(2, 0), new Vector2Int(2, 1), new Vector2Int(2, 2) },
        new[] { new Vector2Int(0, 0), new Vector2Int(1, 1), new Vector2Int(2, 2) },
        new[] { new Vector2Int(2, 0), new Vector2Int(1, 1), new Vector2Int(0, 2) }
    };

    void Awake()
    {
        InitialisePieces();
        DebugLog("Level2Manager initialised");
    }

    /// <summary>
    /// Samples live positions each frame and routes them through placement, movement, and win checks.
    /// </summary>
    void Update()
    {
        if (phase == GamePhase.Completed)
        {
            return;
        }

        foreach (var piece in pieces.Values)
        {
            if (!TryResolvePosition(piece.Identifier, out var worldPosition))
            {
                continue;
            }

            piece.LastKnownPosition = worldPosition;
            if (!TryConvertToBoardCoordinate(worldPosition, out var cell))
            {
                continue;
            }

            if (!piece.BoardPosition.HasValue)
            {
                TryHandlePlacement(piece, cell);
                continue;
            }

            if (piece.BoardPosition.Value != cell)
            {
                TryHandleMove(piece, cell);
            }
        }
    }

    void InitialisePieces()
    {
        pieces.Clear();
        phase = GamePhase.Placement;
        currentPlayer = PlayerId.One;
        gameFinished = false;
        winner = PlayerId.One;
        remainingPlacements.Clear();

        AddPlayerPieces(PlayerId.One, playerOne);
        AddPlayerPieces(PlayerId.Two, playerTwo);
        EnsureMinimumPieces(PlayerId.One, 3);
        EnsureMinimumPieces(PlayerId.Two, 3);

        UpdatePhaseFromPlacements();

        if (pieces.Count == 0)
        {
            DebugLog("No pieces configured.");
        }
    }

    void AddPlayerPieces(PlayerId owner, PlayerConfig config)
    {
        EnsurePlacementEntry(owner);
        if (config == null || config.pieceIdentifiers == null)
        {
            return;
        }

        foreach (var id in config.pieceIdentifiers)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                continue;
            }

            var trimmed = id.Trim();
            var uniqueId = EnsureUniqueIdentifier(trimmed);
            pieces[uniqueId] = new PieceState(owner, uniqueId);
            remainingPlacements[owner]++;
        }
    }

    void EnsureMinimumPieces(PlayerId owner, int minimum)
    {
        var current = CountPiecesForOwner(owner);
        for (var i = current; i < minimum; i++)
        {
            var identifier = EnsureUniqueIdentifier(string.Concat(owner, "_Piece", i + 1));
            pieces[identifier] = new PieceState(owner, identifier);
            EnsurePlacementEntry(owner);
            remainingPlacements[owner]++;
        }
    }

    int CountPiecesForOwner(PlayerId owner)
    {
        var count = 0;
        foreach (var piece in pieces.Values)
        {
            if (piece.Owner == owner)
            {
                count++;
            }
        }
        return count;
    }

    string EnsureUniqueIdentifier(string baseId)
    {
        if (string.IsNullOrEmpty(baseId))
        {
            baseId = "piece";
        }

        var candidate = baseId;
        var counter = 1;
        while (pieces.ContainsKey(candidate))
        {
            counter++;
            candidate = string.Concat(baseId, "#", counter);
        }
        return candidate;
    }

    void EnsurePlacementEntry(PlayerId owner)
    {
        if (!remainingPlacements.ContainsKey(owner))
        {
            remainingPlacements[owner] = 0;
        }
    }

    /// <summary>
    /// Attempts to place an unseated piece into the requested board cell for the active player.
    /// </summary>
    void TryHandlePlacement(PieceState piece, Vector2Int destination)
    {
        if (piece.Owner != currentPlayer)
        {
            return;
        }

        if (!CanPlayerPlace(piece.Owner))
        {
            return;
        }

        if (occupiedCells.ContainsKey(destination))
        {
            return;
        }

        PlacePiece(piece, destination);

        RegisterPlacement(piece.Owner);
        UpdatePhaseFromPlacements();

        if (!CheckForWin(piece.Owner))
        {
            AdvanceTurn();
        }
    }

    /// <summary>
    /// Attempts to move a placed piece into an adjacent cell once that player has no remaining placements.
    /// </summary>
    void TryHandleMove(PieceState piece, Vector2Int destination)
    {
        if (!CanPlayerMove(piece.Owner))
        {
            return;
        }

        if (piece.Owner != currentPlayer)
        {
            return;
        }

        if (!piece.BoardPosition.HasValue)
        {
            return;
        }

        var origin = piece.BoardPosition.Value;
        if (!AreCellsAdjacent(origin, destination))
        {
            DebugLog($"Illegal move for {piece.Identifier}: {origin} -> {destination}");
            return;
        }

        if (occupiedCells.ContainsKey(destination))
        {
            DebugLog($"Destination {destination} already occupied.");
            return;
        }

        occupiedCells.Remove(origin);
        PlacePiece(piece, destination);

        if (!CheckForWin(piece.Owner))
        {
            AdvanceTurn();
        }
    }

    void RegisterPlacement(PlayerId player)
    {
        if (remainingPlacements.TryGetValue(player, out var remaining) && remaining > 0)
        {
            remainingPlacements[player] = remaining - 1;
            if (enableDebugLogging)
            {
                Debug.Log($"[Level2Manager] {GetPlayerName(player)} placements remaining: {remainingPlacements[player]}");
            }
        }
    }

    void UpdatePhaseFromPlacements()
    {
        var newPhase = AllPiecesPlaced ? GamePhase.Movement : GamePhase.Placement;
        if (phase == newPhase)
        {
            return;
        }

        phase = newPhase;
        if (phase == GamePhase.Movement)
        {
            DebugLog("All pieces placed. Movement phase begins.");
        }
    }

    void PlacePiece(PieceState piece, Vector2Int destination)
    {
        piece.BoardPosition = destination;
        occupiedCells[destination] = piece.Identifier;

        if (enableDebugLogging)
        {
            Debug.Log($"[Level2Manager] {piece.Identifier} placed at {destination} by {piece.Owner}");
        }
    }

    bool CheckForWin(PlayerId player)
    {
        foreach (var line in WinningLines)
        {
            var ownsLine = true;
            foreach (var cell in line)
            {
                if (!occupiedCells.TryGetValue(cell, out var occupant) || pieces[occupant].Owner != player)
                {
                    ownsLine = false;
                    break;
                }
            }

            if (ownsLine)
            {
                phase = GamePhase.Completed;
                gameFinished = true;
                winner = player;
                DebugLog($"{GetPlayerName(player)} wins with line {FormatLine(line)}");
                return true;
            }
        }

        return false;
    }

    void AdvanceTurn()
    {
        currentPlayer = currentPlayer == PlayerId.One ? PlayerId.Two : PlayerId.One;
        DebugLog($"Turn advances to {GetPlayerName(currentPlayer)} (phase: {phase})");
    }

    bool TryConvertToBoardCoordinate(Vector3 position, out Vector2Int cell)
    {
        var planar = new Vector2(position.x, position.z);
        var relative = planar - boardOrigin;
        cell = new Vector2Int(-1, -1);

        if (relative.x < 0f || relative.y < 0f)
        {
            return false;
        }

        var gridX = Mathf.FloorToInt(relative.x / cellSize.x);
        var gridY = Mathf.FloorToInt(relative.y / cellSize.y);

        if (gridX < 0 || gridX >= BoardSize || gridY < 0 || gridY >= BoardSize)
        {
            return false;
        }

        var center = GetCellCenter(new Vector2Int(gridX, gridY));
        var distance = Vector2.Distance(planar, center);
        if (distance > cellSnapTolerance)
        {
            return false;
        }

        cell = new Vector2Int(gridX, gridY);
        return true;
    }

    public Vector2 GetCellCenter(Vector2Int cell)
    {
        var centerOffset = new Vector2((cell.x + 0.5f) * cellSize.x, (cell.y + 0.5f) * cellSize.y);
        return boardOrigin + centerOffset;
    }

    public Vector3 GetCellWorldCenter(Vector2Int cell, float height = 0f)
    {
        var planar = GetCellCenter(cell);
        return new Vector3(planar.x, height, planar.y);
    }

    bool AllPiecesPlaced
    {
        get
        {
            foreach (var kvp in remainingPlacements)
            {
                if (kvp.Value > 0)
                {
                    return false;
                }
            }
            return true;
        }
    }

    bool CanPlayerPlace(PlayerId player)
    {
        return remainingPlacements.TryGetValue(player, out var remaining) && remaining > 0;
    }

    bool CanPlayerMove(PlayerId player)
    {
        return remainingPlacements.TryGetValue(player, out var remaining) && remaining == 0;
    }

    bool AreCellsAdjacent(Vector2Int origin, Vector2Int destination)
    {
        if (origin == destination)
        {
            return false;
        }

        if (origin == CenterCell || destination == CenterCell)
        {
            return true;
        }

        var delta = destination - origin;
        return Mathf.Abs(delta.x) + Mathf.Abs(delta.y) == 1;
    }

    bool TryResolvePosition(string identifier, out Vector3 position)
    {
        position = default;
        if (string.IsNullOrEmpty(identifier))
        {
            return false;
        }

        if (spawner != null)
        {
            if (TryResolveFromSpawner(identifier, out position))
            {
                return true;
            }
        }

        if (!allowManualSceneObjects)
        {
            return false;
        }

        var manual = ResolveManualObject(identifier);
        if (manual == null)
        {
            return false;
        }

        position = manual.transform.position;
        return true;
    }

    bool TryResolveFromSpawner(string identifier, out Vector3 position)
    {
        position = default;
        trackedBuffer.Clear();
        if (spawner.GetTrackedObjects(trackedBuffer) == 0)
        {
            return false;
        }

        foreach (var info in trackedBuffer)
        {
            if (MatchesIdentifier(info.Key, identifier))
            {
                position = info.Instance != null ? info.Instance.transform.position : info.Position;
                return true;
            }
        }

        return false;
    }

    GameObject ResolveManualObject(string identifier)
    {
        if (manualLookup.TryGetValue(identifier, out var cached) && cached != null)
        {
            return cached;
        }

        var target = GameObject.Find(identifier);
        manualLookup[identifier] = target;
        if (target == null && enableDebugLogging)
        {
            Debug.Log($"[Level2Manager] Manual object '{identifier}' not found in scene");
        }
        return target;
    }

    static bool MatchesIdentifier(string key, string identifier)
    {
        if (string.Equals(key, identifier, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        if (string.IsNullOrEmpty(key))
        {
            return false;
        }

        var separatorIndex = key.LastIndexOf("::", StringComparison.Ordinal);
        if (separatorIndex >= 0 && separatorIndex + 2 < key.Length)
        {
            var label = key.Substring(separatorIndex + 2);
            if (string.Equals(label, identifier, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }
        return false;
    }

    string GetPlayerName(PlayerId id)
    {
        return id switch
        {
            PlayerId.One => string.IsNullOrEmpty(playerOne.name) ? "Player One" : playerOne.name,
            PlayerId.Two => string.IsNullOrEmpty(playerTwo.name) ? "Player Two" : playerTwo.name,
            _ => id.ToString()
        };
    }

    string FormatLine(IEnumerable<Vector2Int> line)
    {
        return string.Join(", ", line);
    }

    void DebugLog(string message)
    {
        if (!enableDebugLogging)
        {
            return;
        }
        Debug.Log($"[Level2Manager] {message}");
    }

#if UNITY_EDITOR
    [ContextMenu("Spawn Debug Pieces")]
    /// <summary>
    /// Instantiates (or repositions) a full set of pieces for both players so the board can be exercised in editor.
    /// </summary>
    public void SpawnDebugPieces()
    {
        if (pieces.Count == 0)
        {
            InitialisePieces();
        }

        var origin = debugSpawnOrigin;
        var right = Vector3.right * debugSpawnSpacing.x;
        var forward = Vector3.forward * debugSpawnSpacing.y;
        var up = Vector3.up * debugSpawnYOffset;

        SpawnDebugRow(PlayerId.One, origin + up, right, forward, null, 0);
        SpawnDebugRow(PlayerId.Two, origin + up, right, forward, null, 1);
    }

    void SpawnDebugRow(PlayerId owner, Vector3 origin, Vector3 right, Vector3 forward, Transform parent, int row)
    {
        var ownedPieces = GetPiecesForOwner(owner);
        if (ownedPieces.Count == 0)
        {
            return;
        }

        var index = 0;
        foreach (var piece in ownedPieces)
        {
            var identifier = piece.Identifier;
            var position = origin + right * index + forward * row;
            var instance = SpawnOrRepositionDebugPiece(identifier, position, parent);
            if (enableDebugLogging && instance != null)
            {
                Debug.Log($"[Level2Manager] Debug piece '{identifier}' positioned at {position}");
            }
            index++;
        }
    }

    List<PieceState> GetPiecesForOwner(PlayerId owner)
    {
        var result = new List<PieceState>();
        foreach (var piece in pieces.Values)
        {
            if (piece.Owner == owner)
            {
                result.Add(piece);
            }
        }
        return result;
    }

    GameObject SpawnOrRepositionDebugPiece(string identifier, Vector3 position, Transform parent)
    {
        var rotation = parent != null ? parent.rotation : Quaternion.identity;
        var existing = FindExistingPiece(identifier);
        if (existing != null)
        {
#if UNITY_EDITOR
            if (!Application.isPlaying)
            {
                Undo.RecordObject(existing.transform, "Move Debug Piece");
            }
#endif
            existing.transform.SetParent(parent, true);
            existing.transform.SetPositionAndRotation(position, rotation);
            manualLookup[identifier] = existing;
            return existing;
        }

        var prefab = GetPrefabForIdentifier(identifier);
        GameObject instance;
        if (prefab != null)
        {
            if (Application.isPlaying)
            {
                instance = Instantiate(prefab, position, rotation, parent);
            }
            else
            {
                instance = PrefabUtility.InstantiatePrefab(prefab, parent) as GameObject;
                if (instance == null)
                {
                    instance = Instantiate(prefab, position, rotation, parent);
                }
                else
                {
                    instance.transform.SetPositionAndRotation(position, rotation);
                }
#if UNITY_EDITOR
                if (instance != null)
                {
                    Undo.RegisterCreatedObjectUndo(instance, "Spawn Debug Piece");
                }
#endif
            }
        }
        else
        {
            instance = GameObject.CreatePrimitive(PrimitiveType.Cube);
            instance.transform.SetParent(parent, true);
            instance.transform.SetPositionAndRotation(position, rotation);
#if UNITY_EDITOR
            Undo.RegisterCreatedObjectUndo(instance, "Spawn Debug Piece");
#endif
        }

        instance.name = identifier;
        manualLookup[identifier] = instance;
        return instance;
    }

    GameObject FindExistingPiece(string identifier)
    {
        if (manualLookup.TryGetValue(identifier, out var cached) && cached != null)
        {
            return cached;
        }

        var found = GameObject.Find(identifier);
        if (found != null)
        {
            manualLookup[identifier] = found;
        }
        return found;
    }

    GameObject GetPrefabForIdentifier(string identifier)
    {
        var label = ExtractLabel(identifier);
        return spawner != null ? spawner.GetPrefabForLabel(label) : null;
    }

    static string ExtractLabel(string identifier)
    {
        if (string.IsNullOrEmpty(identifier))
        {
            return string.Empty;
        }

        var separatorIndex = identifier.LastIndexOf("::", StringComparison.Ordinal);
        if (separatorIndex >= 0 && separatorIndex + 2 < identifier.Length)
        {
            return identifier.Substring(separatorIndex + 2);
        }

        var hashIndex = identifier.IndexOf('#');
        if (hashIndex > 0)
        {
            return identifier.Substring(0, hashIndex);
        }

        return identifier;
    }

    [CustomEditor(typeof(Level2Manager))]
    class Level2ManagerEditor : Editor
    {
        public override void OnInspectorGUI()
        {
            base.OnInspectorGUI();

            using (new EditorGUI.DisabledScope(EditorApplication.isCompiling))
            {
                if (GUILayout.Button("Spawn Debug Pieces"))
                {
                    foreach (var target in targets)
                    {
                        if (target is Level2Manager manager)
                        {
                            manager.SpawnDebugPieces();
                        }
                    }
                }
            }
        }
    }
#endif
}
