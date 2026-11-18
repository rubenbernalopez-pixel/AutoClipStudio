using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;

namespace AutoClipStudio.WPF.Controls;

/// <summary>
/// Control for displaying a subtitle line with editable words.
/// </summary>
public class SubtitleLineControl : Control
{
    static SubtitleLineControl()
    {
        DefaultStyleKeyProperty.OverrideMetadata(typeof(SubtitleLineControl), new FrameworkPropertyMetadata(typeof(SubtitleLineControl)));
    }

    #region Dependency Properties

    public static readonly DependencyProperty IndexProperty =
        DependencyProperty.Register(nameof(Index), typeof(int), typeof(SubtitleLineControl), new PropertyMetadata(0));

    public int Index
    {
        get => (int)GetValue(IndexProperty);
        set => SetValue(IndexProperty, value);
    }

    public static readonly DependencyProperty StartProperty =
        DependencyProperty.Register(nameof(Start), typeof(double), typeof(SubtitleLineControl), new PropertyMetadata(0.0));

    public double Start
    {
        get => (double)GetValue(StartProperty);
        set => SetValue(StartProperty, value);
    }

    public static readonly DependencyProperty EndProperty =
        DependencyProperty.Register(nameof(End), typeof(double), typeof(SubtitleLineControl), new PropertyMetadata(0.0));

    public double End
    {
        get => (double)GetValue(EndProperty);
        set => SetValue(EndProperty, value);
    }

    public static readonly DependencyProperty TextProperty =
        DependencyProperty.Register(nameof(Text), typeof(string), typeof(SubtitleLineControl), new PropertyMetadata(""));

    public string Text
    {
        get => (string)GetValue(TextProperty);
        set => SetValue(TextProperty, value);
    }

    public static readonly DependencyProperty WordsProperty =
        DependencyProperty.Register(nameof(Words), typeof(IList<SubtitleWordViewModel>), typeof(SubtitleLineControl), new PropertyMetadata(null));

    public IList<SubtitleWordViewModel> Words
    {
        get => (IList<SubtitleWordViewModel>)GetValue(WordsProperty);
        set => SetValue(WordsProperty, value);
    }

    #endregion
}

/// <summary>
/// View model for a subtitle word in the editor.
/// </summary>
public class SubtitleWordViewModel : DependencyObject
{
    public static readonly DependencyProperty WordTextProperty =
        DependencyProperty.Register(nameof(WordText), typeof(string), typeof(SubtitleWordViewModel), new PropertyMetadata(""));

    public string WordText
    {
        get => (string)GetValue(WordTextProperty);
        set => SetValue(WordTextProperty, value);
    }

    public static readonly DependencyProperty OriginalWordProperty =
        DependencyProperty.Register(nameof(OriginalWord), typeof(string), typeof(SubtitleWordViewModel), new PropertyMetadata(null));

    public string? OriginalWord
    {
        get => (string?)GetValue(OriginalWordProperty);
        set => SetValue(OriginalWordProperty, value);
    }

    public static readonly DependencyProperty StartProperty =
        DependencyProperty.Register(nameof(Start), typeof(double), typeof(SubtitleWordViewModel), new PropertyMetadata(0.0));

    public double Start
    {
        get => (double)GetValue(StartProperty);
        set => SetValue(StartProperty, value);
    }

    public static readonly DependencyProperty EndProperty =
        DependencyProperty.Register(nameof(End), typeof(double), typeof(SubtitleWordViewModel), new PropertyMetadata(0.0));

    public double End
    {
        get => (double)GetValue(EndProperty);
        set => SetValue(EndProperty, value);
    }

    public static readonly DependencyProperty ConfidenceProperty =
        DependencyProperty.Register(nameof(Confidence), typeof(double), typeof(SubtitleWordViewModel), new PropertyMetadata(1.0));

    public double Confidence
    {
        get => (double)GetValue(ConfidenceProperty);
        set => SetValue(ConfidenceProperty, value);
    }

    public static readonly DependencyProperty IsCorrectedProperty =
        DependencyProperty.Register(nameof(IsCorrected), typeof(bool), typeof(SubtitleWordViewModel), new PropertyMetadata(false));

    public bool IsCorrected
    {
        get => (bool)GetValue(IsCorrectedProperty);
        set => SetValue(IsCorrectedProperty, value);
    }

    public static readonly DependencyProperty StateProperty =
        DependencyProperty.Register(nameof(State), typeof(SubtitleWordState), typeof(SubtitleWordViewModel), new PropertyMetadata(SubtitleWordState.Pending));

    public SubtitleWordState State
    {
        get => (SubtitleWordState)GetValue(StateProperty);
        set => SetValue(StateProperty, value);
    }

    public static readonly DependencyProperty IndexProperty =
        DependencyProperty.Register(nameof(Index), typeof(int), typeof(SubtitleWordViewModel), new PropertyMetadata(0));

    public int Index
    {
        get => (int)GetValue(IndexProperty);
        set => SetValue(IndexProperty, value);
    }

    public static readonly DependencyProperty LineIndexProperty =
        DependencyProperty.Register(nameof(LineIndex), typeof(int), typeof(SubtitleWordViewModel), new PropertyMetadata(0));

    public int LineIndex
    {
        get => (int)GetValue(LineIndexProperty);
        set => SetValue(LineIndexProperty, value);
    }
}

public enum SubtitleWordState
{
    Pending,
    Active,
    Done,
    Corrected,
    LowConfidence
}