using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Markup.Xaml;
using JpegRecoveryUI.Models;
using System.Threading.Tasks;
using JpegRecoveryLibrary;
using Avalonia.Media.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System;
using Avalonia.Threading;
using Avalonia.Data.Core;
using System.ComponentModel;

namespace JpegRecoveryUI
{
    public class MainWindow : Window
    {
        private ProgressBar _progress;
        private Button _run_btn;
        private Button _browse_btn;
        private TextBlock _result;
        private ComboBox _optComboBox;
        private CheckBox jpegCheckBox;
        private CheckBox videoCheckBox;
        public MainWindow()
        {
            char sep = Path.DirectorySeparatorChar;
            InitializeComponent();
            this.DataContext = new TxtViewModel() {
                //Path = @"C:\Users\Ahmad\Desktop\QCRIInternship\Code\jpeg-carver-csharp-master\Dataset\Original\full_dragon.jpg",
                Imagepath = new Bitmap(string.Format("..{0}..{0}..{0}..{0}..{0}..{0}images{0}CSRG.png",sep))
            };

            _progress = this.FindControl<ProgressBar>("progress");
            _run_btn = this.FindControl<Button>("runBtn");
            _browse_btn = this.FindControl<Button>("browseBtn");
            _result = this.FindControl<TextBlock>("result");
            _optComboBox = this.Find<ComboBox>("optComboBox");
            jpegCheckBox = this.FindControl<CheckBox>("jpegCheckBox");
            videoCheckBox = this.Find<CheckBox>("videoCheckBox");

#if DEBUG
            this.AttachDevTools();
#endif
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }

        public async Task<string> GetPath(string title)
        {
            OpenFileDialog dialog = new OpenFileDialog
            {
                AllowMultiple = false,
                Title = title, 
                /*Filters = new List<FileDialogFilter>
                    {
                        new FileDialogFilter {Name = "Pictures", Extensions = new List<string> {"png", "jpg"}}
                    }*/
            };
            //dialog.Filters.Add(new FileDialogFilter() { Name = "Text", Extensions = { "txt" } });

            string[] result = await dialog.ShowAsync(this);

            //if (result != null)
            //{
            //    await GetPath();
            //}

            return string.Join(" ", result);
        }

        public async void Browse_Clicked(object sender, RoutedEventArgs args)
        {
            string _path = await GetPath("Choose a picture file to load");

            var context = this.DataContext as TxtViewModel;
            context.Path = _path;
        }
        
        


        public async void Run_Clicked(object sender, RoutedEventArgs args)
        {
            var context = this.DataContext as TxtViewModel;
            string outMsg = "";
            _result.Text = ""+ _optComboBox.SelectedIndex;
            var watch = System.Diagnostics.Stopwatch.StartNew();
            _progress.Value = 10;
            _run_btn.IsEnabled = false;
            _browse_btn.IsEnabled = false;


            //Video carving
            if (videoCheckBox.IsChecked == true)
            {
                Procedures p5 = new Procedures();

                string workingDirectory = Directory.GetCurrentDirectory();
                char sep = Path.DirectorySeparatorChar;
                String[] listStrLineElements = workingDirectory.Split(sep);

                workingDirectory = "";
                foreach (String item in listStrLineElements)
                {
                    if (item.Equals("file_carver"))
                        break;
                    workingDirectory += item + sep;
                }



                

                string envFile = string.Format("{0}video_carver_env",
                    workingDirectory, sep);

                string pyFile= string.Format("{0}video_carver{1}orphanFrameRecovery.py", workingDirectory, sep); 

                string pythonFile = string.Format("{0}{1}bin{2}python3",
                    envFile, sep, sep);

                if (!Directory.Exists(envFile))
                {

                    string _path = "find the path!!";
                    string userName = Environment.UserName;

                    _result.Text = "The conda path is being waited!!";
                    _progress.Value = 0;

                    if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                    {
                        _path = string.Format("/home/{0}/anaconda3/bin/conda", userName);
                    }
                    else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
                    {
                        _path = string.Format("/Users/{0}/anaconda3/bin/conda", userName);
                        if (!File.Exists(_path))
                            _path = string.Format("~/opt/anaconda3/bin/conda", userName);
                        if (!File.Exists(_path))
                            _path = string.Format("/opt/anaconda3/bin/conda", userName);
                    }
                    else if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                    {
                        _path = string.Format("C:\\Users\\{0}\\Anaconda3\\bin\\conda.exe", userName);
                        if (!File.Exists(_path))
                            _path = string.Format("C:\\Users\\{0}\\Anaconda3\\Scripts\\conda.exe", userName);
                    }

                    if (!File.Exists(_path))
                    {
                        /*
                        string message = "Video Carver needs to anaconda. Please select the conda path before procoding!!";
                        string title = "Get Conda Path";
                        MessageBoxButtons buttons = MessageBoxButtons.OKCancel;
                        DialogResult result = MessageBox.Show(message, title, buttons, MessageBoxIcon.Warning);
                        if (result == DialogResult.Ok)
                        {
                        */
                        //this.Close();

                        _path = await GetPath("Choose the conda path!!");

                    }


                    _result.Text = "Video carving environment is being created!!";
                    _progress.Value = 5;
                    await Task.Run(() =>
                    {
                        p5.runCMD(_path, string.Format(" create --prefix {0} python=3.7 -y", envFile));
                    });

                    _result.Text = "Requirements are being installed!!";
                    if (!File.Exists(pythonFile))
                        pythonFile = string.Format("{0}{1}python.exe",
                            envFile, sep);
                    _progress.Value = 10;
                    await Task.Run(() =>
                    {
                        p5.runCMD(pythonFile, string.Format(" -m pip install -r {0}video_carver{1}requirements.txt", workingDirectory, sep));
                    });
                    /*
                    }
                    else if (result == DialogResult.Cancel)
                    {
                        this.Close();
                        outMsg = "Video Carver needs to conda. Process is aborted!!!";

                    }
                    */

                }

                if (!File.Exists(pythonFile))
                    pythonFile = string.Format("{0}{1}python.exe",
                        envFile, sep);

                if (File.Exists(pythonFile))
                {
                    _result.Text = "Video carver is started!!";
                    _progress.Value = 15;

                    string outFile = "";
                    try
                    {
                        await Task.Run(() =>
                        {
                            if (_optComboBox.SelectedIndex == 0)
                            {
                                var result = p5.procedure_5(context.Path, "file",pythonFile,pyFile);
                                outFile = result.Item1;
                                outMsg = result.Item2;
                            }
                            if (_optComboBox.SelectedIndex == 1 || _optComboBox.SelectedIndex == 2)
                            {
                                var result = p5.procedure_5(context.Path, "notFile", pythonFile, pyFile);
                                outFile = result.Item1;
                                outMsg = result.Item2;
                            }
                        });
                    }
                    catch (System.Exception e)
                    {
                        outMsg = "Error - " + e.Message;
                    }

                    //If jpeg is recovered then assign bitmap to display in GUI
                    if (File.Exists(outFile))
                    {
                        context.Imagepath = new Bitmap(outFile);
                    }
                }

            }

            if (jpegCheckBox.IsChecked == true)
            {
                if (_optComboBox.SelectedIndex == 0)
                {//Jpeg carving
                
                    _result.Text = " JPEG carving is started";
                    Procedures p1 = new Procedures();
                    string outFile = "";
                    try
                    {
                        await Task.Run(() =>
                        {
                            var result = p1.procedure_1(context.Path);
                            outFile = result.Item1;
                            outMsg = result.Item2;
                        });
                    }
                    catch (System.Exception e)
                    {
                        outMsg = "Error - " + e.Message;
                    }

                    //If jpeg is recovered then assign bitmap to display in GUI
                    if (File.Exists(outFile))
                    {
                        context.Imagepath = new Bitmap(outFile);
                    }
                }
                
                else if (_optComboBox.SelectedIndex == 1)
                {//Storage carving
                    Procedures p2 = new Procedures();
                    string outFile = "";
                    try
                    {

                        await Task.Run(() =>
                        {
                            var result = p2.procedure_2(context.Path);
                            outFile = result.Item1;
                            outMsg = result.Item2 == "Success" ? "Check output image fragments in input path" : result.Item2;
                        });
                    }
                    catch (System.Exception e)
                    {
                        outMsg = "Error - " + e.Message;
                    }

                }
                else if (_optComboBox.SelectedIndex == 2)
                {//Network packet carving
                    Procedures p3 = new Procedures();
                    string outFile = "";
                    try
                    {
                        await Task.Run(() =>
                        {
                            var result = p3.procedure_3(context.Path);
                            outFile = result.Item1;
                            outMsg = result.Item2 == "Success" ? "Check output image fragments in input path" : result.Item2;
                        });

                    }
                    catch (System.Exception e)
                    {
                        outMsg = "Error - " + e.Message;
                    }
                }
                else if (_optComboBox.SelectedIndex == 3)
                {//Check if file fragment is jpeg
                    Procedures p4 = new Procedures();
                    string outFile = "";
                    try
                    {
                        await Task.Run(() =>
                        {
                            var result = p4.procedure_4(context.Path);
                            outFile = result.Item1;
                            outMsg = result.Item2;
                        });

                    }
                    catch (System.Exception e)
                    {
                        outMsg = "Error - " + e.Message;
                    }
                }
            
            }

            _result.Text = outMsg;
            _run_btn.IsEnabled = true;
            _browse_btn.IsEnabled = true;
            _progress.Value = 100;
            watch.Stop();
            var elapsedMs = watch.ElapsedMilliseconds;
        }

    }
}
