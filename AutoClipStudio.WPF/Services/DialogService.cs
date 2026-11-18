using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using Microsoft.Win32;
using AutoClipStudio.WPF.Services;

namespace AutoClipStudio.WPF.Services;

/// <summary>
/// Dialog service for file dialogs, message boxes, etc.
/// </summary>
public interface IDialogService
{
    Task<string?> OpenFileDialogAsync(string title, string filter, string? initialDirectory = null);
    Task<string?> SaveFileDialogAsync(string title, string filter, string defaultFileName, string? initialDirectory = null);
    Task<string?> OpenFolderDialogAsync(string title, string? initialDirectory = null);
    Task<MessageBoxResult> ShowMessageAsync(string message, string title, MessageBoxButton buttons, MessageBoxImage icon);
    Task<bool> ShowConfirmationAsync(string message, string title);
    Task<string?> ShowInputDialogAsync(string message, string title, string defaultValue = "");
}

public class DialogService : IDialogService
{
    public Task<string?> OpenFileDialogAsync(string title, string filter, string? initialDirectory = null)
    {
        var tcs = new TaskCompletionSource<string?>();
        Application.Current.Dispatcher.Invoke(() =>
        {
            var dialog = new OpenFileDialog
            {
                Title = title,
                Filter = filter,
                InitialDirectory = initialDirectory ?? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
            };
            tcs.SetResult(dialog.ShowDialog() == true ? dialog.FileName : null);
        });
        return tcs.Task;
    }

    public Task<string?> SaveFileDialogAsync(string title, string filter, string defaultFileName, string? initialDirectory = null)
    {
        var tcs = new TaskCompletionSource<string?>();
        Application.Current.Dispatcher.Invoke(() =>
        {
            var dialog = new SaveFileDialog
            {
                Title = title,
                Filter = filter,
                FileName = defaultFileName,
                InitialDirectory = initialDirectory ?? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                OverwritePrompt = true
            };
            tcs.SetResult(dialog.ShowDialog() == true ? dialog.FileName : null);
        });
        return tcs.Task;
    }

    public Task<string?> OpenFolderDialogAsync(string title, string? initialDirectory = null)
    {
        var tcs = new TaskCompletionSource<string?>();
        Application.Current.Dispatcher.Invoke(() =>
        {
            // Use OpenFileDialog with folder selection hack, or use Win32 API
            // For simplicity, using a custom dialog or the system folder picker
            var dialog = new OpenFileDialog
            {
                Title = title,
                Filter = "Folders|*.none",
                FileName = "Seleccionar carpeta",
                CheckFileExists = false,
                CheckPathExists = true,
                ValidateNames = false,
                InitialDirectory = initialDirectory ?? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
            };

            // This is a workaround - in production, use a proper folder picker
            if (dialog.ShowDialog() == true)
            {
                tcs.SetResult(Path.GetDirectoryName(dialog.FileName));
            }
            else
            {
                tcs.SetResult(null);
            }
        });
        return tcs.Task;
    }

    public Task<MessageBoxResult> ShowMessageAsync(string message, string title, MessageBoxButton buttons, MessageBoxImage icon)
    {
        var tcs = new TaskCompletionSource<MessageBoxResult>();
        Application.Current.Dispatcher.Invoke(() =>
        {
            tcs.SetResult(MessageBox.Show(message, title, buttons, icon));
        });
        return tcs.Task;
    }

    public Task<bool> ShowConfirmationAsync(string message, string title)
    {
        return ShowMessageAsync(message, title, MessageBoxButton.YesNo, MessageBoxImage.Question)
            .ContinueWith(t => t.Result == MessageBoxResult.Yes);
    }

    public Task<string?> ShowInputDialogAsync(string message, string title, string defaultValue = "")
    {
        var tcs = new TaskCompletionSource<string?>();
        Application.Current.Dispatcher.Invoke(() =>
        {
            var dialog = new InputDialog(message, title, defaultValue);
            if (dialog.ShowDialog() == true)
            {
                tcs.SetResult(dialog.ResponseText);
            }
            else
            {
                tcs.SetResult(null);
            }
        });
        return tcs.Task;
    }
}

/// <summary>
/// Simple input dialog.
/// </summary>
public partial class InputDialog : Window
{
    public string ResponseText { get; private set; } = "";

    public InputDialog(string message, string title, string defaultValue)
    {
        InitializeComponent();
        Title = title;
        MessageText.Text = message;
        InputTextBox.Text = defaultValue;
        InputTextBox.SelectAll();
        InputTextBox.Focus();
    }

    private void OkButton_Click(object sender, RoutedEventArgs e)
    {
        ResponseText = InputTextBox.Text;
        DialogResult = true;
        Close();
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}