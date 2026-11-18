namespace AutoClipStudio.Core.Interop;

/// <summary>
/// JSON-RPC message for communication with Python backend.
/// </summary>
public class PythonMessage
{
    public string JsonRpc { get; set; } = "2.0";
    public string? Method { get; set; }
    public object? Params { get; set; }
    public object? Result { get; set; }
    public PythonError? Error { get; set; }
    public object? Id { get; set; }

    public static PythonMessage CreateRequest(string method, object? paramsObj = null, object? id = null)
    {
        return new PythonMessage
        {
            Method = method,
            Params = paramsObj,
            Id = id ?? Guid.NewGuid().ToString()
        };
    }

    public static PythonMessage CreateNotification(string method, object? paramsObj = null)
    {
        return new PythonMessage
        {
            Method = method,
            Params = paramsObj,
            Id = null // Notifications don't have IDs
        };
    }

    public static PythonMessage CreateResponse(object? result, object? id)
    {
        return new PythonMessage
        {
            Result = result,
            Id = id
        };
    }

    public static PythonMessage CreateErrorResponse(int code, string message, object? id)
    {
        return new PythonMessage
        {
            Error = new PythonError { Code = code, Message = message },
            Id = id
        };
    }
}

/// <summary>
/// JSON-RPC error object.
/// </summary>
public class PythonError
{
    public int Code { get; set; }
    public string Message { get; set; } = "";
    public object? Data { get; set; }
}

/// <summary>
/// Progress notification from Python backend.
/// </summary>
public class ProgressNotification
{
    public string Stage { get; set; } = "";
    public double Percent { get; set; }
    public string Message { get; set; } = "";
    public int CurrentItem { get; set; }
    public int TotalItems { get; set; }
    public double? EtaSeconds { get; set; }
}